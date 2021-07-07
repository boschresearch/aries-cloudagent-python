import logging

from pydid import DID, DIDDocument, DIDDocumentBuilder

from ..wallet.base import BaseWallet
from ..core.profile import ProfileSession
from .util import (
    retrieve_did_document,
    save_did_document,
    VerificationMethod,
)

LOGGER = logging.getLogger(__name__)


class DIDWeb:
    """Class for managing a did:web DID document."""

    def __init__(self, session: ProfileSession):
        """
        Initialize DIDWeb.

        Args:
            session: The current profile session
        """
        self._session = session

    @property
    def session(self) -> ProfileSession:
        """
        Accessor for the current profile session.

        Returns:
            The current profile session

        """
        return self._session

    async def create_from_wallet(self, did: DID, extras=None) -> str:
        """Add content from wallet to DID document."""
        wallet = self.session.inject(BaseWallet, required=False)
        public_did_obj = await wallet.get_public_did()
        recipient_key = public_did_obj.verkey
        endpoint = public_did_obj.metadata["endpoint"]
        did_document = DIDDocument
        builder = DIDDocumentBuilder(did)
        vmethod = builder.verification_method.add(
            VerificationMethod[public_did_obj.key_type.name].value,
            ident="key-1",
            public_key_base58=recipient_key,
        )
        builder.authentication.reference(vmethod.id)
        builder.assertion_method.reference(vmethod.id)
        if endpoint:
            builder.service.add_didcomm(
                service_endpoint=endpoint,
                recipient_keys=[vmethod],
                routing_keys=[],
            )

        if extras is not None:
            if "verification_methods" in extras:
                verification_methods = extras["verification_methods"]
                for idx, verification_method in enumerate(verification_methods):
                    did = verification_method["did"]
                    did_info = await wallet.get_local_did(did)
                    key_type = did_info.key_type
                    vmethod = builder.verification_method.add(
                        VerificationMethod[key_type.name].value,
                        # +2 since there's already the key related to the public DID
                        ident=f"key-{idx+2}",
                        public_key_base58=did_info.verkey,
                    )
                    if "verification_relationships" in verification_method:
                        vrelations = verification_method["verification_relationships"]
                        for vrelation in vrelations:
                            getattr(builder, vrelation).reference(vmethod.id)

            if "services" in extras:

                services = extras["services"]
                for service in services:
                    builder.service.add(
                        type_=service["type"],
                        service_endpoint=service["service_endpoint"],
                    )

        did_document = builder.build()

        await save_did_document(did_document, self._session)
        self._did_document = did_document
        return did_document.serialize()

    async def create(self, did_document) -> str:
        await save_did_document(None, self._session)
        self._did_document = did_document
        return did_document

    async def delete(self):
        await save_did_document(None, self._session)
        return None

    async def retrieve(self) -> str:
        did_document = await retrieve_did_document(self._session)
        if did_document:
            return did_document.serialize()
        else:
            return None
