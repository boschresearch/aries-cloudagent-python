"""Open Policy Agent Plugin."""

# import json

import aiohttp
import asyncio
import logging
import re

from ..messaging.responder import BaseResponder
from ..config.injection_context import InjectionContext
from ..core.protocol_registry import ProtocolRegistry
from ..core.event_bus import Event, EventBus
from ..core.profile import Profile
from ..indy.util import generate_pr_nonce

from ..connections.models.conn_record import ConnRecord
from ..messaging.decorators.attach_decorator import AttachDecorator
from ..protocols.didexchange.v1_0.manager import DIDXManager
from ..protocols.present_proof.v1_0.manager import PresentationManager
from ..protocols.present_proof.v1_0.message_types import (
    ATTACH_DECO_IDS,
    PRESENTATION_REQUEST,
)
from ..protocols.present_proof.v1_0.messages.presentation_request import (
    PresentationRequest,
)

# from ..admin.server import AdminServer

LOGGER = logging.getLogger(__name__)

EVENT_PATTERN_RECORD = re.compile("^acapy::record::([^:]*)(?:::.*)?$")


class Opa:
    """Open Policy Agent."""

    def __init__(self, context: InjectionContext):
        self._context = context
        self._opa_base_url = "http://host.docker.internal:8181/v1/data/"

        event_bus = self._context.inject(EventBus, required=False)
        if event_bus:
            event_bus.subscribe(EVENT_PATTERN_RECORD, self._on_record_event)

    async def _on_record_event(self, profile: Profile, event: Event):
        match = EVENT_PATTERN_RECORD.search(event.topic)
        topic = match.group(1) if match else None
        LOGGER.info("OPA Message received: %s", topic)
        input_dict = {"input": event.payload}
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self._opa_base_url + topic, json=input_dict
            ) as response:
                resp_json = await response.json()
                LOGGER.info(resp_json)
                action = resp_json["result"]["action"] if "result" in resp_json else []
                action = action[0] if len(action) > 0 else None
                if action:

                    # Handle actions of type "connection"
                    if action["type"] == "connection":
                        if action["data"]["accept"]:
                            session = await profile.session(self._context)
                            didx_mgr = DIDXManager(session)
                            conn_rec = await ConnRecord.retrieve_by_id(
                                session, event.payload["connection_id"]
                            )

                            async def respond(didx_mgr, conn_rec, session):
                                await asyncio.sleep(2)
                                didx_resp = await didx_mgr.create_response(conn_rec)
                                responder = session.inject(BaseResponder, required=True)
                                if responder:
                                    await responder.send_reply(
                                        didx_resp, connection_id=conn_rec.connection_id
                                    )

                            loop = asyncio.get_event_loop()
                            loop.create_task(respond(didx_mgr, conn_rec, session))

                    # Handle actions of type "proof request"
                    elif action["type"] == "proof request":
                        LOGGER.info("Send proof request")
                        session = await profile.session(self._context)
                        connection_id = event.payload["connection_id"]

                        conn_rec = await ConnRecord.retrieve_by_id(
                            session, connection_id
                        )

                        indy_proof_request = action["data"]["proof_request"]
                        if not indy_proof_request.get("nonce"):
                            indy_proof_request["nonce"] = await generate_pr_nonce()

                        presentation_request_message = PresentationRequest(
                            request_presentations_attach=[
                                AttachDecorator.data_base64(
                                    mapping=indy_proof_request,
                                    ident=ATTACH_DECO_IDS[PRESENTATION_REQUEST],
                                )
                            ],
                        )

                        presentation_manager = PresentationManager(profile)

                        await presentation_manager.create_exchange_for_request(
                            connection_id=connection_id,
                            presentation_request_message=presentation_request_message,
                        )
                        responder = session.inject(BaseResponder, required=True)
                        if responder:
                            await responder.send(
                                presentation_request_message,
                                connection_id=connection_id,
                            )

                    # Handle actions of type "tag connection"
                    elif action["type"] == "tag connection":
                        LOGGER.info("Tag connection")

    async def setup(self, context: InjectionContext):
        """Perform required setup for OPA Plugin."""
        protocol_registry = await context.inject(ProtocolRegistry)
