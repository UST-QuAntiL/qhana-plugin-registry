# Copyright 2022 University of Stuttgart
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from dataclasses import dataclass
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Sequence,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)

from sqlalchemy.orm import lazyload
from sqlalchemy.orm.query import Query
from sqlalchemy.sql import column, func, select
from sqlalchemy.sql.expression import and_, asc, desc, or_, ColumnElement
from sqlalchemy.sql.selectable import CTE

from .db import DB, MODEL
from .models.model_helpers import IdMixin

M = TypeVar("M", bound=MODEL)
I = TypeVar("I", bound=IdMixin)


@dataclass
class PageInfo:
    """Dataclass for holding information about a page.

    Cursor: the cursor id of the row directly before the page
    Page: the page number (starting with page 1)
    Row: the first row number of the (first item on the) page
    """

    cursor: Union[str, int]
    page: int
    row: int


@dataclass
class PaginationInfo:
    """Dataclass holding pagination information."""

    collection_size: int
    cursor_row: int
    cursor_page: int
    surrounding_pages: List[PageInfo]
    last_page: Optional[PageInfo]
    page_items_query: Query


def get_page_info(
    model: Union[Type[M], Type[I]],
    cursor_column: ColumnElement,
    sortables: Dict[str, ColumnElement],
    cursor: Optional[Union[str, int]],
    sort: Sequence[Tuple[str, str]],
    item_count: int = 25,
    surrounding_pages: int = 5,
    filter_criteria: Sequence[Any] = tuple(),
) -> PaginationInfo:
    if item_count is None:
        item_count = 25

    if "id" not in sortables and issubclass(model, IdMixin):
        sortables["id"] = cast(ColumnElement, model.id)

    order_by_clauses = []
    for col_name, direction in sort:
        sort_direction: Any = desc if direction == "desc" else asc

        sort_column = sortables[col_name]
        if "collate" in sort_column.info:
            order_by_clauses.append(
                sort_direction(sort_column.collate(sort_column.info["collate"]))
            )
        else:
            order_by_clauses.append(sort_direction(sort_column))
    row_numbers: Any = func.row_number().over(order_by=order_by_clauses)

    query_filter: Any = and_(*filter_criteria)

    collection_size: int = DB.session.execute(
        select(func.count())
        .select_from(model)
        .options(lazyload("*"))
        .filter(query_filter)
    ).scalar_one_or_none()

    if cursor is not None:
        # set cursor to none if no cursor is not found
        cursor = (
            # a query with exists is more complex than this
            DB.session.query(
                cursor_column,
            )
            .filter(cursor_column == cursor)
            .scalar()  # none or value of the cursor
        )

    item_query: Query = select(model).filter(query_filter).order_by(*order_by_clauses)

    if collection_size <= item_count:
        return PaginationInfo(
            collection_size=collection_size,
            cursor_row=0,
            cursor_page=1,
            surrounding_pages=[],
            last_page=PageInfo(0, 1, 0),
            page_items_query=item_query.limit(item_count),
        )

    cursor_row: Union[int, Any] = 0

    if cursor is not None:
        if filter_criteria:
            # always include cursor row
            query_filter = [or_(cursor_column == cursor, and_(*filter_criteria))]
        else:
            query_filter = []

        item_query = select(model).filter(*query_filter).order_by(*order_by_clauses)

        cursor_row_cte: CTE = (
            DB.session.query(
                row_numbers.label("row"),
                cursor_column,
            )
            .filter(*query_filter)
            .from_self(column("row"))
            .filter(cursor_column == cursor)
            .cte("cursor_row")
        )
        cursor_row = cursor_row_cte.c.row

    page_rows = (
        DB.session.query(
            cursor_column,
            row_numbers.label("row"),
            (row_numbers / item_count).label("page"),
            (row_numbers % item_count).label("modulo"),
        )
        .filter(*query_filter)
        .order_by(column("row").asc())
        .cte("pages")
    )

    last_page = (
        DB.session.query(
            row_numbers.label("row"),
            (row_numbers / item_count).label("page"),
        )
        .filter(*query_filter)
        .order_by(column("row").desc())
        .limit(1)
        .cte("last-page")
    )

    pages = (
        DB.session.query(*page_rows.c)
        .only_return_tuples(True)
        .order_by(page_rows.c.row.asc())
        .filter(
            (page_rows.c.modulo == (cursor_row % item_count))  # only return page cursors
            & (  # but not for all pages
                (  # only return the +- surrounding pages pages
                    (page_rows.c.page >= ((cursor_row / item_count) - surrounding_pages))
                    & (
                        page_rows.c.page
                        <= ((cursor_row / item_count) + surrounding_pages)
                    )
                )
                | (
                    page_rows.c.page >= (last_page.c.page - 1)
                )  # also return last 1-2 pages
            )
        )
        .all()
    )

    context_pages, last_page, current_cursor_row, cursor_page = digest_pages(
        pages, cursor, surrounding_pages, collection_size
    )

    return PaginationInfo(
        collection_size=collection_size,
        cursor_row=current_cursor_row,
        cursor_page=cursor_page,
        surrounding_pages=context_pages,
        last_page=last_page,
        page_items_query=item_query.offset(current_cursor_row).limit(item_count),
    )


def digest_pages(
    pages: List[Tuple[Union[str, int], int, int, int]],
    cursor: Optional[Union[str, int]],
    max_surrounding: int,
    collection_size: int,
) -> Tuple[List[PageInfo], Optional[PageInfo], int, int]:
    """Parse the page list from sql and generate PageInfo objects with the correct numbering.
    Also seperate last page from the list if outside of max_surrounding pages bound."""
    CURSOR, ROW, PAGE, MODULO = 0, 1, 2, 3  # row name mapping of tuples in pages

    surrounding_pages: List[PageInfo] = []
    last_page = None
    cursor_row = 0
    cursor_page = 1
    if not pages:
        return surrounding_pages, None, cursor_row, cursor_page

    # offset page numbers from sql query to match correct pages
    # offset by 1 to start with page 1 (0 based in sql)
    # extra offset if first page contains < item_count items (then modulo col in sql is != 0)
    page_offset = 1 if pages and pages[0][MODULO] == 0 else 2

    # collect surrounding pages
    current_count = 0
    for page in pages:
        # test with >= because collection size may not inlcude the cursor item!
        if page[ROW] >= collection_size:
            break  # do not include an empty last page
        if cursor is not None and str(page[CURSOR]) == str(cursor):
            # half way point
            current_count = 0  # reset counter for pages on other side of cursor
            cursor_row = page[ROW]
            cursor_page = page[PAGE] + page_offset
            continue  # exclude the page of the cursor from surrounding pages
        current_count += 1
        if current_count <= max_surrounding:
            surrounding_pages.append(
                PageInfo(
                    cursor=page[CURSOR], page=page[PAGE] + page_offset, row=page[ROW] + 1
                )
            )

    # find last page
    last_page = pages[-1]
    # test with >= because collection size may not inlcude the cursor item!
    if last_page[ROW] >= collection_size:
        if len(pages) > 1:
            last_page = pages[-2]
    return (
        surrounding_pages,
        PageInfo(
            cursor=last_page[CURSOR],
            page=last_page[PAGE] + page_offset,
            row=last_page[ROW] + 1,
        ),
        cursor_row,
        cursor_page,
    )
