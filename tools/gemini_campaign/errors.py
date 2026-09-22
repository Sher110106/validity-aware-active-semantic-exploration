class BrokerError(RuntimeError):
    """Base error that never includes credentials or transport payloads."""

class PolicyError(BrokerError): pass
class LedgerError(BrokerError): pass
class AccountingHalt(BrokerError): pass
class CredentialError(BrokerError): pass
