"""Public Profile admin routes."""

from aiohttp import web
from aiohttp_apispec import docs, request_schema, response_schema
from aiohttp_apispec.decorators import response

from marshmallow import fields

from ...admin.request_context import AdminRequestContext

from ...wallet.base import BaseWallet
from ...indy.holder import IndyHolder, IndyHolderError

from ..models.openapi import OpenAPISchema


class CreatePublicProfileRequestSchema(OpenAPISchema):
    """Create Public Profile content in W3C VC JSON-LD"""

    credential_ids = fields.List(
        fields.Str(description="VC IDs to be published in public profile."),
        required=True
    )
    verkey = fields.Str(required=True, description="verkey to use for signing")

class CreatePublicProfileResponseSchema(OpenAPISchema):
    """Response schema for CreatePublicProfile"""
    profile = fields.Dict(required=True)


@docs(tags=["profile"], summary="Create and publish public profile in W3C JSON-LD from existing AnonCred credentials")
@request_schema(CreatePublicProfileRequestSchema())
@response_schema(CreatePublicProfileResponseSchema(), 200, description="")
async def create_public_profile(request: web.BaseRequest):
    vcs = []
    context: AdminRequestContext = request["context"]
    credential_ids = request.match_info["credential_ids"]
    verkey = request.match_info["verkey"]
    session = await context.session()

    holder = session.inject(IndyHolder)
    for id in credential_ids:
        credential = await holder.get_credential(id)
        credential_json = json.loads(credential)
        vcs.append(credential_json)
    profile = {}
    profile["verifiableCredentials"] = vcs
    return web.json_response(profile)


async def register(app: web.Application):
    """Register routes."""

    app.add_routes([web.post("/profile/publish", create_public_profile)])
