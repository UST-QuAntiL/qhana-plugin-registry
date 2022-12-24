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

"""Utilities for creating resource keys, links, data and full api responses."""

from dataclasses import dataclass, field
from itertools import chain
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Type, Union

from sqlalchemy.exc import ArgumentError

from .base_models import ApiLink, ApiResponse, BaseApiObject
from .base_models import CollectionResource as CollectionResponse
from .base_models import (
    CursorPage,
    DeletedApiObject,
    DeletedApiObjectRaw,
    NewApiObject,
    NewApiObjectRaw,
    ChangedApiObject,
    ChangedApiObjectRaw,
)


@dataclass()
class EmbeddedResource:
    resource: Any


@dataclass()
class CollectionResource:
    resource_type: Type
    resource: Optional[Any] = None
    collection_size: int = 0
    item_links: Optional[Sequence[ApiLink]] = None


@dataclass()
class PageResource:
    resource_type: Type
    resource: Optional[Any] = None
    page_number: int = 1
    active_page: int = 1
    last_page: Optional[int] = None
    collection_size: int = 0
    item_links: Optional[Sequence[ApiLink]] = None
    extra_arguments: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_first(self) -> bool:
        return self.page_number == 1

    @property
    def is_last(self) -> bool:
        return self.last_page is not None and self.page_number == self.last_page

    @property
    def is_prev(self) -> bool:
        return self.page_number + 1 == self.active_page

    @property
    def is_next(self) -> bool:
        return self.page_number - 1 == self.active_page

    def get_page(self, page_number: int):
        return PageResource(
            page_number=page_number,
            resource_type=self.resource_type,
            resource=self.resource,
            active_page=self.active_page,
            last_page=self.last_page,
            collection_size=self.collection_size,
            extra_arguments=self.extra_arguments,
        )


def query_params_to_api_key(query_params: Dict[str, str]) -> Dict[str, str]:
    key = {}
    for k, v in query_params.items():
        key[f"?{k}"] = str(v)
    return key


class KeyGenerator:
    """Base class (and registry) of all api key generators.

    Usage:

    >>> KeyGenerator.generate_key(MyResource(db_id=1, ...), query_params)
    {"my-resource-id": "1"}  # key content depends on invoked KeyGenerator


    Implement a new Generator:

    >>> class MyResourceKeyGenerator(KeyGenerator, resource_type=MyResource, page=False):
    >>>     def update_key(self, key, resource):
    >>>         assert isinstance(resource, MyResource)
    >>>         key.update({"my-resource-id": str(resource.db_id)})
    >>>         return key

    Set ``page=True`` to implement a KeyGenerator for a ``PageResource`` of the
    given resource type.
    """

    __generators: Dict[Type, "KeyGenerator"] = {}

    __generators_for_page_resources: Dict[Type, "KeyGenerator"] = {}

    def __init_subclass__(cls, **kwargs) -> None:
        resource_type = kwargs.pop("resource_type", None)
        if resource_type is None:
            raise ArgumentError(
                "A key generator class must provide a valid resource type!"
            )
        is_page = kwargs.pop("page", False)
        generators = (
            KeyGenerator.__generators_for_page_resources
            if is_page
            else KeyGenerator.__generators
        )
        if resource_type in generators:
            raise ArgumentError(
                f"The resource type '{resource_type}' already has a key generator!"
                f"\t(registered: {generators[resource_type]}, offending class: {cls})"
            )
        generators[resource_type] = cls()

    @staticmethod
    def generate_key(
        resource,
        query_params: Optional[Dict[str, str]] = None,
        base_key: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:
        """Generate an api key object for the given resource.

        The KeyGenerator will be selected based on the resource type.

        Args:
            resource: the resource to generate the api key for
            query_params (Optional[Dict[str, str]]): Optional query params to include in the key. Defaults to None.
            base_key (Optional[Dict[str, str]]): Optional base key. Duplicate entries will be overridden. Defaults to None.

        Returns:
            Dict[str, str]: the generated api key
        """
        key: Dict[str, str] = {}

        # prepare base key
        if base_key:
            key.update(base_key)
        if query_params:
            key.update(query_params_to_api_key(query_params=query_params))

        # look up key generator
        if isinstance(resource, (PageResource, CollectionResource)):
            generator = KeyGenerator.__generators_for_page_resources.get(
                resource.resource_type
            )
        else:
            generator = KeyGenerator.__generators.get(type(resource))

        # invoke generator
        if generator:  # TODO print warning if generator is missing?
            return generator.update_key(key, resource)
        return key

    def update_key(self, key: Dict[str, str], resource) -> Dict[str, str]:
        """Update the given api key with the key attributes of the current resource.

        The method should update the key in place or return a new key created
        from the old key to allow combining keys from different generators.

        This method can invoke the key generator of a parent resource of the
        given resource.

        Args:
            key (Dict[str, str]): the api key to update
            resource: the resource to generate the api key for

        Returns:
            Dict[str, str]: the updated key
        """
        raise NotImplementedError()


LINK_ACTIONS = {"create", "update", "delete", "restore"}


class LinkGenerator:
    """Base class (and registry) of all api link generators.

    Usually the link generator uses a KeyGenerator to generate the api keys required
    for the api links.

    Usage:

    >>> LinkGenerator.get_link_of(MyResource(db_id=1, ...), query_params=query_params)
    ApiLink(href="/my-resource/1/", ...)  # content depends on invoked LinkGenerator

    >>> LinkGenerator.get_links_for(MyResource(db_id=1, ...), ["create", "delete"], include_default_relations=False)
    [ApiLink(href="/my-resource/", ...), ApiLink(href="/my-resource/1/", ...)]  # content depends on invoked LinkGenerator


    Implement a new Generator:

    >>> class MyResourceLinkGenerator(LinkGenerator, resource_type=MyResource, relation="create", page=True):
    >>>     def generate_link(self, resource, *, query_params: Optional[Dict[str, str]] = None) -> Optional[ApiLink]:
    >>>         ...
    >>>         return ApiLink(...)
    """

    __generators: Dict[Union[None, Type, Tuple[Type, str]], "LinkGenerator"] = {}

    __generators_for_page_resources: Dict[
        Union[None, Type, Tuple[Type, str]], "LinkGenerator"
    ] = {}

    def __init_subclass__(cls, **kwargs) -> None:
        resource_type: Type = kwargs.pop("resource_type", None)
        relation: str = kwargs.pop(
            "relation", None
        )  # None relation implies self as relation
        key = resource_type if relation is None else (resource_type, relation)
        is_page = kwargs.pop("page", False)
        generators = (
            LinkGenerator.__generators_for_page_resources
            if is_page
            else LinkGenerator.__generators
        )
        if key in generators:
            raise ArgumentError(
                f"The resource type '{resource_type}' with action '{relation}' already has a link generator!"
                f"\t(registered: {generators[key]}, offending class: {cls})"
            )
        generators[key] = cls()

    @staticmethod
    def _get_generators_and_resource_type(resource):
        is_page = isinstance(resource, (PageResource, CollectionResource))

        generators = (
            LinkGenerator.__generators_for_page_resources
            if is_page
            else LinkGenerator.__generators
        )
        resource_type: Type = resource.resource_type if is_page else type(resource)
        return generators, resource_type

    @staticmethod
    def get_links_for(
        resource,
        relations: Optional[Iterable[str]] = None,
        include_default_relations: bool = True,
    ):
        """Get a list of links that should be included in the api response of the given resource.

        By default links for the relation ``"up"`` and the relations defined in ``LINK_ACTIONS``
        are generated.

        Args:
            resource: the resource to generate the links for
            relations (Optional[Iterable[str]]): a list of relations to generate links for. Defaults to None.
            include_default_relations (bool, optional): if links for default relations should be included. Defaults to True.

        Returns:
            Sequence[ApiLink]: the generated api links
        """
        links: List[ApiLink] = []

        generators, resource_type = LinkGenerator._get_generators_and_resource_type(
            resource
        )
        link_relations: Iterable[str] = relations if relations is not None else []
        if include_default_relations:
            link_relations = chain(link_relations, ("up", *LINK_ACTIONS))
        for rel in link_relations:
            generator = generators.get((resource_type, rel))
            if generator is not None:
                link = generator.generate_link(resource)
                if link is not None:
                    links.append(link)

        return links

    @staticmethod
    def get_link_of(
        resource,
        *,
        query_params: Optional[Dict[str, str]] = None,
        extra_relations: Optional[Sequence[str]] = None,
        for_relation: Optional[str] = None,
    ) -> Optional[ApiLink]:
        """Get an api link for a specific resource (and relation).

        Args:
            resource: the resource to generate the api link for
            query_params (Optional[Dict[str, str]]): query params to include in the generated link (and key). Defaults to None.
            extra_relations (Optional[Sequence[str]], optional): extra relations to include in the links rel attribute. Defaults to None.
            for_relation (Optional[str], optional): the relation to generate a link for. None is the "self" relation. Defaults to None.

        Raises:
            KeyError: no generator found for the given resource type (and relation)

        Returns:
            Optional[ApiLink]: the generated api link (or ``None`` if the link would be invalid, e.g., a "create" relation link that is only available for authenticated users)
        """
        is_page = isinstance(resource, PageResource)

        # find generator
        generators, resource_type = LinkGenerator._get_generators_and_resource_type(
            resource
        )
        generator = (
            generators.get(resource_type)
            if for_relation is None
            else generators.get((resource_type, for_relation))
        )

        if generator is not None:
            link = generator.generate_link(resource, query_params=query_params)

            if link is None:
                return None

            # add relations to link
            extra_rels: List[str] = []

            # add page related relations
            if is_page and for_relation is None:
                if resource.is_first:
                    extra_rels.append("first")
                if resource.is_last:
                    extra_rels.append("last")
                if resource.is_prev:
                    extra_rels.append("prev")
                if resource.is_next:
                    extra_rels.append("next")
                extra_rels.append(f"page-{resource.page_number}")
            if extra_relations:
                link.rel = tuple(set(chain(link.rel, extra_rels, extra_relations)))
            else:
                link.rel = tuple(set(chain(link.rel, extra_rels)))
            return link

        raise KeyError(
            f"No link generator found for resource type '{resource_type}' (for rel '{'self' if for_relation is None else for_relation}')."
        )

    def generate_link(
        self, resource, *, query_params: Optional[Dict[str, str]] = None
    ) -> Optional[ApiLink]:
        """Generate a the api link for the (resource, relation) key of this LinkGenerator.

        For each (resource, relation) there should be exactly one LinkGenerator
        implementing this method.

        Args:
            resource: the resource to generate the link for
            query_params (Optional[Dict[str, str]], optional): optional query params to include in the link. Defaults to None.

        Returns:
            Optional[ApiLink]: the generated api link for the (resource, relation) key of this LinkGenerator.
        """
        raise NotImplementedError()


class ApiObjectGenerator:
    """Base class (and registry) of all api object generators.

    Usually the api object generator uses a LinkGenerator to generate the api links required
    for the api objects.

    Usage:

    >>> ApiObjectGenerator.get_api_object(MyResource(db_id=1, ...))
    MyResourceApiObject(self=ApiLink(...), ...)  # content depends on invoked ApiObjectGenerator


    Implement a new Generator:

    >>> class MyResourceApiObjectGenerator(ApiObjectGenerator, resource_type=MyResource):
    >>>     def generate_api_object(self, resource, *, query_params: Optional[Dict[str, str]] = None) -> Optional[MyResourceApiObject]:
    >>>         ...
    >>>         return MyResourceApiObject(...)
    """

    __generators: Dict[Type, "ApiObjectGenerator"] = {}

    def __init_subclass__(cls, **kwargs) -> None:
        resource_type: Type = kwargs.pop("resource_type", None)

        generators = ApiObjectGenerator.__generators
        if resource_type in generators:
            raise ArgumentError(
                f"The resource type '{resource_type}' already has an api object dataclass generator!"
                f"\t(registered: {generators[resource_type]}, offending class: {cls})"
            )
        generators[resource_type] = cls()

    @staticmethod
    def get_api_object(
        resource,
        *,
        query_params: Optional[Dict[str, str]] = None,
    ) -> Optional[BaseApiObject]:
        """Get an ApiObject representation of the given resource.

        ApiObjects can be directly set as the ``data`` attribute of an api response.

        If no generator is found then an empty ApiObject with only the self link will be generated.

        Args:
            resource: the resource to generate the api object for
            query_params (Optional[Dict[str, str]]): query params to include in the self link (usually passed to the LinkGenerator). Defaults to None.

        Returns:
            Optional[BaseApiObject]: the generated api object (or ``None`` if the resource should never be serialized, e.g., a resource for which a user has insufficient rights)
        """
        resource_type = type(resource)

        generators = ApiObjectGenerator.__generators

        generator = generators.get(resource_type)
        if generator is None:
            return ApiObjectGenerator.default_generate_api_object(
                resource, query_params=query_params
            )

        return generator.generate_api_object(resource, query_params=query_params)

    @staticmethod
    def default_generate_api_object(
        resource,
        *,
        query_params: Optional[Dict[str, str]] = None,
    ) -> Optional[BaseApiObject]:
        """Generate an empty api object with only a self link."""
        self_link = LinkGenerator.get_link_of(resource, query_params=query_params)
        if self_link is None:
            return None
        return BaseApiObject(self=self_link)

    def generate_api_object(
        self,
        resource,
        *,
        query_params: Optional[Dict[str, str]] = None,
    ) -> Optional[BaseApiObject]:
        """Build an api object from the given resource.

        Args:
            resource: the resource to build an api object from
            query_params (Optional[Dict[str, str]], optional): query params to include in the seld link of the resource. Defaults to None.

        Returns:
            Optional[BaseApiObject]: the built resource (or ``None`` if the resource should never be serialized, e.g., a resource for which a user has insufficient rights)
        """
        raise NotImplementedError()


class CollectionResourceApiObjectGenerator(
    ApiObjectGenerator, resource_type=CollectionResource
):
    """An api object generator for collection resources."""

    def generate_api_object(
        self,
        resource: CollectionResource,
        *,
        query_params: Optional[Dict[str, str]] = None,
    ) -> Optional[BaseApiObject]:
        assert isinstance(resource, CollectionResource)

        # TODO handle authorization

        self_link = LinkGenerator.get_link_of(resource, query_params=query_params)

        assert self_link is not None

        return CollectionResponse(
            self=self_link,
            collection_size=resource.collection_size,
            items=(resource.item_links if resource.item_links else []),
        )


class CursorPageApiObjectGenerator(ApiObjectGenerator, resource_type=PageResource):
    """An api object generator for page resources."""

    def generate_api_object(
        self,
        resource: PageResource,
        *,
        query_params: Optional[Dict[str, str]] = None,
    ) -> Optional[BaseApiObject]:
        assert isinstance(resource, PageResource)

        # TODO handle authorization

        self_link = LinkGenerator.get_link_of(resource, query_params=query_params)

        assert self_link is not None

        return CursorPage(
            self=self_link,
            collection_size=resource.collection_size,
            page=resource.page_number,
            items=(resource.item_links if resource.item_links else []),
        )


class EmbeddedApiObjectGenerator(ApiObjectGenerator, resource_type=EmbeddedResource):
    """An api object generator for embedded api objects."""

    def generate_api_object(
        self,
        resource: EmbeddedResource,
        *,
        query_params: Optional[Dict[str, str]] = None,
    ) -> Optional[BaseApiObject]:
        assert isinstance(resource, EmbeddedResource)

        # return the embedded resource raw (not as api object) as the schema will
        # call the corresponding ApiObjectGenerator during serialization!
        return resource.resource


class DeletedApiObjectGenerator(ApiObjectGenerator, resource_type=DeletedApiObjectRaw):
    """An api object generator for deleted api objects."""

    def generate_api_object(
        self,
        resource: DeletedApiObjectRaw,
        *,
        query_params: Optional[Dict[str, str]] = None,
    ) -> Optional[BaseApiObject]:
        assert isinstance(resource, DeletedApiObjectRaw)
        deleted_link = LinkGenerator.get_link_of(
            resource.deleted, extra_relations=(DELETED_REL,)
        )
        assert deleted_link is not None
        self_link = LinkGenerator.get_link_of(resource.deleted, for_relation=DELETE_REL)
        assert self_link is not None
        self_link.resource_type = DELETED_REL

        forward_link = None

        if resource.redirect_to:
            if isinstance(resource.redirect_to, ApiLink):
                forward_link = resource.redirect_to
            else:
                forward_link = LinkGenerator.get_link_of(resource.redirect_to)

        return DeletedApiObject(
            self=self_link, deleted=deleted_link, redirect_to=forward_link
        )


class ApiResponseGenerator:
    """Base class (and registry) of all api response generators.

    Usually the api response generator uses an ApiObjectGenerator to generate the api objects required
    for the api response.

    Usage:

    >>> ApiResponseGenerator.get_api_response(MyResource(db_id=1, ...))
    ApiResponse(links=[...], data=ApiObject(...), ...)  # content depends on invoked ApiResponseGenerator


    Implement a new Generator:

    >>> class MyResourceApiResponseGenerator(ApiResponseGenerator, resource_type=MyResource):
    >>>     def generate_api_response(self, resource, *, query_params: Optional[Dict[str, str]] = None) -> Optional[ApiResponse]:
    >>>         ...
    >>>         return ApiResponse(links=[...], data=ApiObject(...), ...)
    """

    __generators: Dict[Type, "ApiResponseGenerator"] = {}

    def __init_subclass__(cls, **kwargs) -> None:
        resource_type: Type = kwargs.pop("resource_type", None)
        generators = ApiResponseGenerator.__generators
        if resource_type in generators:
            raise ArgumentError(
                f"The resource type '{resource_type}' already has an api response dataclass generator!"
                f"\t(registered: {generators[resource_type]}, offending class: {cls})"
            )
        generators[resource_type] = cls()

    @staticmethod
    def get_api_response(
        resource,
        *,
        query_params: Optional[Dict[str, str]] = None,
        link_to_relations: Optional[Iterable[str]] = None,
        include_default_relations: bool = True,
        extra_links: Optional[Sequence[ApiLink]] = None,
        extra_embedded: Optional[Sequence[ApiResponse]] = None,
    ) -> Optional[ApiResponse]:
        """Get an api response object built from the given resource.

        Args:
            resource: the resource to build the api response for.
            query_params (Optional[Dict[str, str]]): query params to be passed to the ApiObjectGenerator. Defaults to None.
            link_to_relations (Optional[Iterable[str]]): include links for the specified relations. Defaults to None.
            include_default_relations (bool, optional): include links for the default relations (``"up"`` and all ``LINK_ACTIONS``). Defaults to True.
            extra_links (Optional[Sequence[ApiLink]]): a list of api links to additionally include. Defaults to None.
            extra_embedded (Optional[Sequence[ApiResponse]]): a list of ApiResponses to include as embedded responses. Defaults to None.

        Returns:
            Optional[ApiResponse]: the built api response (or ``None`` if the resource should never be serialized, e.g., a resource for which a user has insufficient rights)
        """
        resource_type = type(resource)

        # find generator
        generators = ApiResponseGenerator.__generators
        generator = generators.get(resource_type)

        response: Optional[ApiResponse]

        # generate api response
        if generator is None:
            response = ApiResponseGenerator.default_generate_api_response(
                resource,
                query_params=query_params,
                link_to_relations=link_to_relations,
                include_default_relations=include_default_relations,
            )
        else:
            response = generator.generate_api_response(
                resource,
                query_params=query_params,
                link_to_relations=link_to_relations,
                include_default_relations=include_default_relations,
            )

        if response is None:
            return None

        # add extra links and embedded responses
        if extra_links:
            response.links = (*response.links, *extra_links)
        if extra_embedded:
            if response.embedded:
                response.embedded = (*response.embedded, *extra_embedded)
            else:
                response.embedded = extra_embedded
        return response

    @staticmethod
    def default_generate_api_response(
        resource,
        *,
        query_params: Optional[Dict[str, str]] = None,
        link_to_relations: Optional[Iterable[str]] = None,
        include_default_relations: bool = True,
    ) -> Optional[ApiResponse]:
        """Generate a default api response.

        Uses the ``TYPE_TO_METADATA`` map to determine the relations to generate
        links for if the resource is an instance of ``EmbeddedResource``.

        Args:
            resource: the resource to generate the response for
            query_params (Optional[Dict[str, str]]): the query params for the self link. Defaults to None.
            link_to_relations (Optional[Iterable[str]]): the relations to link to. Defaults to None.
            include_default_relations (bool, optional): include default relations. Defaults to True.

        Returns:
            Optional[ApiResponse]: the generated api response (or ``None`` if the resource should never be serialized, e.g., a resource for which a user has insufficient rights)
        """
        is_embedded = isinstance(resource, EmbeddedResource)
        links_resource = resource.resource if is_embedded else resource
        if is_embedded:
            meta = tm.TYPE_TO_METADATA.get(type(links_resource))
            if meta:
                if link_to_relations is None:
                    link_to_relations = meta.extra_link_rels
                else:
                    link_to_relations = chain(link_to_relations, meta.extra_link_rels)

        api_object = ApiObjectGenerator.get_api_object(
            resource, query_params=query_params
        )

        if api_object is None:
            return None

        return ApiResponse(
            links=LinkGenerator.get_links_for(
                links_resource,
                relations=link_to_relations,
                include_default_relations=include_default_relations,
            ),
            data=api_object,
        )

    def generate_api_response(
        self,
        resource,
        *,
        query_params: Optional[Dict[str, str]] = None,
        link_to_relations: Optional[Iterable[str]] = None,
        include_default_relations: bool = True,
    ) -> Optional[ApiResponse]:
        """Build an api response from the given resource.

        Args:
            resource: the resource to build the api response from
            query_params (Optional[Dict[str, str]]): query params to be passed to the api object generator. Defaults to None.
            link_to_relations (Optional[Iterable[str]]): relations to generate links for and include in the response. Defaults to None.
            include_default_relations (bool, optional): include the default relations. Defaults to True.

        Returns:
            Optional[ApiResponse]: the api response (or ``None`` if the resource should never be serialized, e.g., a resource for which a user has insufficient rights)
        """
        raise NotImplementedError()


class NewApiObjectApiResponseGenerator(
    ApiResponseGenerator, resource_type=NewApiObjectRaw
):
    """An api response generator for "new" api objects."""

    def generate_api_response(
        self,
        resource: NewApiObjectRaw,
        *,
        query_params: Optional[Dict[str, str]] = None,
        link_to_relations: Optional[Iterable[str]] = None,
        include_default_relations: bool = True,
    ) -> Optional[ApiResponse]:
        embedded_response = ApiResponseGenerator.get_api_response(
            EmbeddedResource(resource.new)
        )
        assert embedded_response is not None
        created_link = LinkGenerator.get_link_of(resource.new)
        assert isinstance(created_link, ApiLink)

        self_link = LinkGenerator.get_link_of(
            resource.self,
            query_params=query_params,
            extra_relations=(CREATE_REL, POST_REL, created_link.resource_type),
        )
        assert self_link is not None
        self_link.resource_type = NEW_REL
        return ApiResponse(
            links=LinkGenerator.get_links_for(
                resource.self,
                relations=link_to_relations,
                include_default_relations=include_default_relations,
            )
            + [created_link],
            data=NewApiObject(self=self_link, new=created_link),
            embedded=[embedded_response],
        )


class ChangedApiObjectApiResponseGenerator(
    ApiResponseGenerator, resource_type=ChangedApiObjectRaw
):
    """An api response generator for "changed" api objects."""

    def generate_api_response(
        self,
        resource: ChangedApiObjectRaw,
        *,
        query_params: Optional[Dict[str, str]] = None,
        link_to_relations: Optional[Iterable[str]] = None,
        include_default_relations: bool = True,
    ) -> Optional[ApiResponse]:
        embedded_response = ApiResponseGenerator.get_api_response(
            EmbeddedResource(resource.changed)
        )
        assert embedded_response is not None
        changed_link = LinkGenerator.get_link_of(resource.changed)
        assert isinstance(changed_link, ApiLink)

        if resource.self is None:
            self_link = changed_link.copy_with(
                resource_type=CHANGED_REL,
                rel=(*changed_link.rel, changed_link.resource_type, UPDATE_REL, PUT_REL),
            )
        elif isinstance(resource.self, ApiLink):
            self_link = resource.self
        else:
            self_link = LinkGenerator.get_link_of(
                resource.self,
                query_params=query_params,
                extra_relations=(UPDATE_REL, PUT_REL, changed_link.resource_type),
            )
            assert self_link is not None
            self_link.resource_type = CHANGED_REL
        return ApiResponse(
            links=LinkGenerator.get_links_for(
                resource.self if resource.self else resource.changed,
                relations=link_to_relations,
                include_default_relations=include_default_relations,
            )
            + [changed_link],
            data=ChangedApiObject(self=self_link, changed=changed_link),
            embedded=[embedded_response],
        )


class DeletedApiObjectApiResponseGenerator(
    ApiResponseGenerator, resource_type=DeletedApiObjectRaw
):
    """An api response generator for "deleted" api objects."""

    def generate_api_response(
        self,
        resource: DeletedApiObjectRaw,
        *,
        query_params: Optional[Dict[str, str]] = None,
        link_to_relations: Optional[Iterable[str]] = None,
        include_default_relations: bool = True,
    ) -> Optional[ApiResponse]:
        return ApiResponse(
            links=LinkGenerator.get_links_for(
                resource.deleted,
                relations=link_to_relations,
                include_default_relations=include_default_relations,
            ),
            data=ApiObjectGenerator.get_api_object(resource, query_params=query_params),
        )


# late imports to avoid circular references
from .generators.constants import (  # isort:skip
    CREATE_REL,
    DELETE_REL,
    DELETED_REL,
    NEW_REL,
    CHANGED_REL,
    POST_REL,
    PUT_REL,
    UPDATE_REL,
)
from .generators import type_map as tm  # isort:skip
