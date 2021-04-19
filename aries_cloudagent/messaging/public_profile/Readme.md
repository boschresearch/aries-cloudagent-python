# Notes
verkey used for example: FA8WrgKepPRgrgPiwLNArrpWpbf8WSHT68WkSkcg2ScE

credential id / referent example used: "f114e7ce-ef10-4ea4-9ee6-6daf99b787e6"



# References
Public profile - Machine-readable, cryptographially-verifiable imprint linked to a DID
https://hackmd.io/@masterdata/SkmOaE2SO

Wrapping Indy Credentials (AnonCreds) in W3C VCs
https://hackmd.io/@masterdata/HkZiQtnrO

# Example
[example_response.jsonld](./example_response.jsonld)

The example validates "true" with acapy jsonld/verify endpoint.


# Todo
- ProofType is not recognized yet
  Which means it's also not part of the VP signature!
- A Verify method for the new proof type is missing
- Key ID is missing in the proof block

- How to get network specific did prefix?

  Option 1: Use configuration to map to prefix

# Questions
- Restrict exported credential attributes?
- Restrict exported credential attribute values? E.g. leave the empty and let the verifier request from the holder.
- Allow to add "claims", which means pure claims, that are not credentials in acapy?
