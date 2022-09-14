# Api Architecture

The QHAna Plugin-Registry exposes a HATEOAS REST-API.
Resources are represented in a custom JSON format originally developed for MUSE4Anything.

```{seealso}
The full documentation of the resource representation format can be found in the [MUSE4Anything documentation](https://muse4anything.readthedocs.io/en/latest/api-doc.html#format-of-api-responses).
```

## Implementation Architecture

The API implementation is split between the view functions and the resource generators.
The view functions are responsible for loading the resources from the database while the generators map the raw resources to their representation.
The generators do not only map the resources from the database to their API representation but also enrich the resources with additional information in the form of hyperlinks.
These hyperlinks form the HATEOAS part of the REST API.


```
┏━ApiResponseGenerator.get_api_response()━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                                                                ┃
┃ links: ┌─LinkGenerator.get_links_for()──────────────────────┐  ┃
┃        │                                                    │  ┃
┃        │ 0: ┌─LinkGenerator.get_link_of()───────────────┐   │  ┃
┃        │    │                                           │   │  ┃
┃        │    │ key: ╭─KeyGenerator.generate_key()─────╮  │   │  ┃
┃        │    │      ╰─────────────────────────────────╯  │   │  ┃
┃        │    └───────────────────────────────────────────┘   │  ┃
┃        │                                                    │  ┃
┃        │ 1: ┌─LinkGenerator.get_link_of()───────────────┐   │  ┃
┃        │    │                                           │   │  ┃
┃        │    │ key: ╭─KeyGenerator.generate_key()─────╮  │   │  ┃
┃        │    │      ╰─────────────────────────────────╯  │   │  ┃
┃        │    └───────────────────────────────────────────┘   │  ┃
┃        └────────────────────────────────────────────────────┘  ┃
┃                                                                ┃
┃ data:  ┌─ApiObjectGenerator.get_api_object()────────────────┐  ┃
┃        │                                                    │  ┃
┃        │ self: ┌─LinkGenerator.get_link_of()────────────┐   │  ┃
┃        │       │                                        │   │  ┃
┃        │       │ key: ╭─KeyGenerator.generate_key()──╮  │   │  ┃
┃        │       │      ╰──────────────────────────────╯  │   │  ┃
┃        │       └────────────────────────────────────────┘   │  ┃
┃        └────────────────────────────────────────────────────┘  ┃
┃                                                                ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```


### The `ApiResponseGenerator`

The {any}`ApiResponseGenerator` maps a resource to an api response object.
The resource itself is mapped to an api object by using the {any}`ApiObjectGenerator`.
Hateoas links are generated from the {any}`LinkGenerator`.

### The `ApiObjectGenerator`

The {any}`ApiObjectGenerator` maps a resource to an api object that can be used in the `data` field of an api response.
It uses the {any}`LinkGenerator` to generate the `self` link of the resource.

### The `LinkGenerator`

The {any}`LinkGenerator` can be used to generate the canonical resource link (or `self` link) of a resource.
It can also generate a list of related links.
The {any}`KeyGenerator` is used to generate the api keys required for the api links.
