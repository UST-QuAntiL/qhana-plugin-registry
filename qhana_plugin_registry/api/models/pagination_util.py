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
from typing import Dict, List, Optional, Sequence, Tuple, Type, TypeVar, Union, cast

from sqlalchemy.sql.expression import ColumnElement, ColumnOperators
from marshmallow.exceptions import ValidationError

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
    sort: Optional[str] = None
    extra_query_params: Optional[Dict[str, str]] = None

    @property
    def order_by(self) -> Sequence[Tuple[str, str]]:
        """The sort query argument."""
        if not self.sort:
            return []
        return [
            ((sort := c.strip()).lstrip("+-"), "desc" if sort.startswith("-") else "asc")
            for c in self.sort.split(",")
            if c
        ]

    def to_query_params(
        self,
        cursor: Optional[Union[str, int]] = "",
        extra_params: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:
        """Generate a dict containing the pagination options as query arguments.

        Args:
            cursor (Optional[Union[str, int]], optional): the cursor to overwrite the current cursor. Defaults to "".
            extra_params (Dict[str, str], optional): extra query params to include in the api link

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

        if self.sort:
            params["sort"] = self.sort

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
    _cast_cursor: Optional[type[str] | type[int]] = None,
) -> PaginationOptions:
    """Prepare pagination query arguments into a PaginationOptions object.

    Args:
        _sort_default (str): a default sort string to apply if sort is None
        _cast_cursor (type[str]|type[int], optional): if set, ensure that the cursor value is either an int or a string. Defaults to None.
        cursor (Optional[Union[str, int]], optional): the cursor of the current page. Defaults to None.
        item_count (int, optional): the current item count. Defaults to 25.
        sort (Optional[str], optional): the current sort argument. Defaults to None.

    Returns:
        PaginationOptions: the prepared PaginationOptions object
    """
    if sort is None and _sort_default is not None:
        sort = _sort_default

    if cursor and _cast_cursor:
        try:
            cursor = _cast_cursor(cursor)
        except ValueError:
            raise ValidationError(
                f"Page cursor was {cursor} but should have been {'a string' if _cast_cursor is str else 'an integer'}!"
            )

    return PaginationOptions(
        sort=sort,
        item_count=item_count,
        cursor=cursor,
    )


M = TypeVar("M", bound=MODEL)
I = TypeVar("I", bound=IdMixin)


def default_get_page_info(
    model: Union[Type[M], Type[I]],
    filter_criteria: Sequence[ColumnOperators],
    pagination_options: PaginationOptions,
    sort_columns: Optional[Dict[str, ColumnElement]] = None,
) -> PaginationInfo:
    """Get the pagination info from a model that extends IdMixin.

    Args:
        model (Type[IdMixin]): the db model; must also extend IdMixin!
        filter_criteria (Sequence[ColumnOperators]): the filter criteria
        pagination_options (PaginationOptions): the pagination options object containing the page size, sort string and cursor
        sort_columns (Optional[Dict[str, Column]], optional): a dict mapping sort_keys to columns of the model that can be used to sort the items. Defaults to None.

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
    id_column = cast(ColumnElement, model.id)

    sort: str = pagination_options.sort if pagination_options.sort else "id"

    if not sort_columns:
        sort_columns = {}
        sort_col_names = [c[0] for c in pagination_options.order_by]

        if not sort_col_names:
            sort_col_names.append("id")

        for name in sort_col_names:
            col_name = name.lstrip("+-")
            sort_column = getattr(model, col_name, None)
            if sort_column is None:
                raise KeyError(f"No column with name '{col_name}' found!", model)
            sort_columns[name] = sort_column

    if not sort_columns:
        raise ValueError("Could not identify sort columns!", model, pagination_options)

    return get_page_info(
        model,
        id_column,
        sort_columns,
        pagination_options.cursor,
        pagination_options.order_by,
        pagination_options.item_count,
        filter_criteria=filter_criteria,
    )


def generate_page_links(
    resource: PageResource,
    pagination_info: PaginationInfo,
    pagination_options: PaginationOptions,
    extra_query_params: Optional[Dict[str, str]] = None,
) -> List[ApiLink]:
    """Generate page links from pagination info and options for the given page resource.

    Args:
        resource (PageResource): the base page resource
        pagination_info (PaginationInfo): the pagination info containing first last and surrounding pages
        pagination_options (PaginationOptions): the pagination options that were used to generate the pagination info
        extra_query_params (Dict[str, str], optional): extra query params to include in all page links

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
                    cursor=pagination_info.last_page.cursor,
                    extra_params=extra_query_params,
                ),
            )

            if last_page_link:
                extra_links.append(last_page_link)

    for page in pagination_info.surrounding_pages:
        if page == pagination_info.last_page:
            continue  # link already included

        page_link = LinkGenerator.get_link_of(
            resource.get_page(page.page),
            query_params=pagination_options.to_query_params(
                cursor=page.cursor,
                extra_params=extra_query_params,
            ),
        )

        if page_link:
            extra_links.append(page_link)
    return extra_links
