"""Public Profile admin routes."""

import json
from pyld import jsonld

from aiohttp import web
from aiohttp_apispec import docs, request_schema, response_schema
from aiohttp_apispec.decorators import response

from marshmallow import fields

from ...admin.request_context import AdminRequestContext

from ...wallet.base import BaseWallet
from ...indy.holder import IndyHolder, IndyHolderError

from ..jsonld.credential import sign_credential, verify_credential

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
    body = await request.json()
    verkey = body.get("verkey")
    credential_ids = body.get("credential_ids")
    session = await context.session()

    wallet = session.inject(BaseWallet, required=False)
    public_did_obj = await wallet.get_public_did()

    holder = session.inject(IndyHolder)
    for id in credential_ids:
        credential = await holder.get_credential(id)
        credential_json = json.loads(credential)
        w3c_vc = build_w3c_credential(credential_json)
        vcs.append(w3c_vc)
    profile = {}
    vp_context = [
        "https://www.w3.org/2018/credentials/v1"
    ]
    profile["@context"] = vp_context
    profile["type"] = "VerifiablePresentation"
    profile["verifiableCredential"] = vcs

    sig_options = {
        "verificationMethod": get_network_did_prefix() + public_did_obj.did,
        "proofPurpose": "assertionMethod"
    }

    compacted = jsonld.compact(profile, vp_context)
    print(json.dumps(compacted, indent=2))
    signed_profile = await sign_credential(profile, sig_options, public_did_obj.verkey, wallet)

    return web.json_response(signed_profile)

def build_w3c_credential(credential):
    vc = {}

    attrs = credential["attrs"]
    cred_def_id = credential["cred_def_id"]
    subject_context = {}
    subject_context["sc"] = get_network_did_prefix() + cred_def_id
    for k,v in attrs.items():
        subject_context[k] = {
            "@id": "sc:" + k
        }
    vc["@context"] = [
        "https://www.w3.org/2018/credentials/v1",
        {"@context": subject_context }
    ]
    vc["type"] = "VerifiableCredential"
    vc["credentialSubject"] = attrs
    proof_type = {
        "type": "IndyCredDefProofType",
        "proofPurpose": "assertionMethod",
        "verificationMethod": get_network_did_prefix() + cred_def_id
    }
    vc["proof"] = proof_type
    return vc

def get_network_did_prefix():
    return "did:sov:iil:"

async def register(app: web.Application):
    """Register routes."""

    app.add_routes([web.post("/profile/create", create_public_profile)])
