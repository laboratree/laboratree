"""Panel domain package: Respondent / ConsentRecord / Invitation persistence models.

The respondent-relationship spine of the Panel CRM. PII lives ONLY here; survey responses link
back solely through the opaque invitation token, so analysis exports stay pseudonymous.
"""
