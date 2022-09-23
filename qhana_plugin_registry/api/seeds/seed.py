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

"""Module containing the resource endpoint of the seeds API."""

from http import HTTPStatus

from flask.views import MethodView
from flask_smorest import abort

from .root import SEEDS_API
from ..models.base_models import (
    DeletedApiObjectRaw,
    DeletedApiObjectSchema,
    get_api_response_schema,
)
from ..models.request_helpers import ApiResponseGenerator, PageResource
from ..models.seeds import SeedSchema
from ...db.db import DB
from ...db.models.seeds import Seed


@SEEDS_API.route("/<string:seed_id>/")
class SeedView(MethodView):
    """Detail endpoint of the seed api."""

    @SEEDS_API.response(HTTPStatus.OK, get_api_response_schema(SeedSchema))
    def get(self, seed_id: str):
        """Get a single seed resource."""
        if not seed_id or not seed_id.isdecimal():
            abort(HTTPStatus.BAD_REQUEST, message="The seedId is in the wrong format!")
        found_seed = Seed.get_by_id(int(seed_id))
        if not found_seed:
            abort(HTTPStatus.NOT_FOUND, message="Seed not found.")

        return ApiResponseGenerator.get_api_response(found_seed)

    @SEEDS_API.response(HTTPStatus.OK, get_api_response_schema(DeletedApiObjectSchema))
    def delete(self, seed_id: str):
        if not seed_id or not seed_id.isdecimal():
            abort(HTTPStatus.BAD_REQUEST, message="The seedId is in the wrong format!")
        found_seed = Seed.get_by_id(int(seed_id))
        if found_seed:
            # FIXME handle related plugins!
            DB.session.delete(found_seed)
            DB.session.commit()
        else:
            # Deleted dummy resource
            found_seed = Seed(int(seed_id), "http://deleted.example.org")

        return ApiResponseGenerator.get_api_response(
            DeletedApiObjectRaw(
                deleted=found_seed, redirect_to=PageResource(Seed, page_number=1)
            )
        )
