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

"""Module containing helpers for pagination that are better suited for the view functions."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Type, TypeVar, Union, cast

from sqlalchemy.sql.schema import Column

from .base_models import ApiLink
from .request_helpers import LinkGenerator, PageResource
from ...db.db import MODEL
from ...db.models.model_helpers import IdMixin
from ...db.pagination import PaginationInfo, get_page_info


@dataclass
class PaginationOptions:
    """Class holding pagination options parsed from query args."""

    item_count: int = 25
    cursor: Optional[Union[str, int]] = None
    sort_order: str = "asc"
    sort_column: Optional[str] = None
    extra_query_params: Optional[Dict[str, str]] = None

    @property
    def sort(self) -> Optional[str]:
        """The sort query argument."""
        if self.sort_column:
            if self.sort_order == "asc":
                return self.sort_column
            elif self.sort_order == "desc":
                return f"-{self.sort_column}"

    def to_query_params(
        self,
        cursor: Optional[Union[str, int]] = "",
        extra_params: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:
        """Generate a dict containing the pagination options as query arguments.

        Args:
            cursor (Optional[Union[str, int]], optional): the cursor to overwrite the current cursor. Defaults to "".

        Returns:
            Dict[str, str]: the query arguments dict
        """
        params = {
            "item-count": str(self.item_count),
        }

        if cursor is None:
            pass  # no cursor
        elif cursor:
            params["cursor"] = str(cursor)
        elif self.cursor:
            params["cursor"] = str(self.cursor)

        sort = self.sort
        if sort:
            params["sort"] = sort

        if self.extra_query_params:
            params.update(self.extra_query_params)

        if extra_params:
            params.update(extra_params)

        return params


def prepare_pagination_query_args(
    *,
    cursor: Optional[Union[str, int]] = None,
    item_count: int = 25,
    sort: Optional[str] = None,
    _sort_default: str,
) -> PaginationOptions:
    """Prepare pagination query arguments into a PaginationOptions object.

    Args:
        _sort_default (str): a default sort string to apply if sort is None
        cursor (Optional[Union[str, int]], optional): the cursor of the current page. Defaults to None.
        item_count (int, optional): the current item count. Defaults to 25.
        sort (Optional[str], optional): the current sort argument. Defaults to None.

    Returns:
        PaginationOptions: the prepared PaginationOptions object
    """
    if sort is None and _sort_default is not None:
        sort = _sort_default
    sort_order = "asc"
    if sort and sort.startswith("-"):
        sort_order = "desc"
    sort_column = sort.lstrip("+-") if sort else None

    return PaginationOptions(
        sort_column=sort_column,
        sort_order=sort_order,
        item_count=item_count,
        cursor=cursor,
    )


M = TypeVar("M", bound=MODEL)
I = TypeVar("I", bound=IdMixin)


def default_get_page_info(
    model: Union[Type[M], Type[I]],
    filter_criteria: Sequence[Any],
    pagination_options: PaginationOptions,
    sort_columns: Optional[Sequence[Column]] = None,
) -> PaginationInfo:
    """Get the pagination info from a model that extends IdMixin.

    Args:
        model (Type[IdMixin]): the db model; must also extend IdMixin!
        filter_criteria (Sequence[Any]): the filter criteria
        pagination_options (PaginationOptions): the pagination options object containing the page size, sort string and cursor
        sort_columns (Optional[Sequence[Column]], optional): a list of columns of the model that can be used to sort the items. Defaults to None.

    Raises:
        TypeError: if model is not an IdMixin
        KeyError: if the sort column could not be found in the model
        ValueError: if no sort column could be identified

    Returns:
        PaginationInfo: the pagination info
    """
    if not issubclass(model, IdMixin):
        raise TypeError(
            "Directly use get_page_info() for models that do not inherit from IdMixin!"
        )
    id_column = cast(Column, model.id)

    sort: str = "id"

    if not sort_columns:
        sort_col_name = pagination_options.sort_column
        if not sort_col_name:
            sort = "id"
        else:
            sort_column = getattr(model, sort_col_name, None)
            if sort_column is None:
                raise KeyError(f"No column with name '{sort_col_name}' found!", model)
            assert pagination_options.sort is not None
            sort = pagination_options.sort
            sort_columns = (sort_column,)

    if not sort_columns:
        raise ValueError("Could not identify sort columns!", model, pagination_options)

    return get_page_info(
        model,
        id_column,
        sort_columns,
        pagination_options.cursor,
        sort,
        pagination_options.item_count,
        filter_criteria=filter_criteria,
    )


def generate_page_links(
    resource: PageResource,
    pagination_info: PaginationInfo,
    pagination_options: PaginationOptions,
) -> List[ApiLink]:
    """Generate page links from pagination info and options for the given page resource.

    Args:
        resource (PageResource): the base page resource
        pagination_info (PaginationInfo): the pagination info containing first last and surrounding pages
        pagination_options (PaginationOptions): the pagination options that were used to generate the pagination info

    Returns:
        List[ApiLink]: a list of api links to the last page and the surrounding pages
    """
    extra_links: List[ApiLink] = []
    if pagination_info.last_page is not None:
        if pagination_info.cursor_page != pagination_info.last_page.page:
            # only if current page is not last page
            last_page_link = LinkGenerator.get_link_of(
                resource.get_page(pagination_info.last_page.page),
                query_params=pagination_options.to_query_params(
                    cursor=pagination_info.last_page.cursor
                ),
            )

            if last_page_link:
                extra_links.append(last_page_link)

    for page in pagination_info.surrounding_pages:
        if page == pagination_info.last_page:
            continue  # link already included

        page_link = LinkGenerator.get_link_of(
            resource.get_page(page.page),
            query_params=pagination_options.to_query_params(cursor=page.cursor),
        )

        if page_link:
            extra_links.append(page_link)
    return extra_links
