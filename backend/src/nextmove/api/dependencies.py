from functools import lru_cache

from nextmove.data.guardian import GuardianProfileRepository, ResilientGuardianProfileRepository
from nextmove.data.snowflake import SnowflakeRepository, SnowflakeSettings
from nextmove.decision.engine import DecisionEngine
from nextmove.integrations.gemini import GeminiClient
from nextmove.integrations.guardian_chat import GuardianGeminiClient
from nextmove.integrations.guardian_providers import GuardianProviderSearchClient
from nextmove.integrations.serpapi import SerpApiClient
from nextmove.services.decision_service import DecisionService
from nextmove.services.guardian_chat import GuardianChatService
from nextmove.services.guardian_market import GuardianMarketEvidenceService
from nextmove.services.guardian_providers import GuardianProviderService
from nextmove.settings import get_settings


@lru_cache
def get_profile_repository() -> SnowflakeRepository:
    settings = get_settings()
    if not settings.snowflake_account or not settings.snowflake_user:
        raise RuntimeError("Snowflake account and user are not configured")
    return SnowflakeRepository(
        SnowflakeSettings(
            account=settings.snowflake_account,
            user=settings.snowflake_user,
            password=settings.snowflake_password,
            authenticator=settings.snowflake_authenticator,
            role=settings.snowflake_role,
            warehouse=settings.snowflake_warehouse,
            database=settings.snowflake_database,
            schema=settings.snowflake_schema,
        )
    )


@lru_cache
def get_guardian_repository() -> GuardianProfileRepository:
    try:
        snowflake = get_profile_repository()
    except RuntimeError:
        snowflake = None
    return ResilientGuardianProfileRepository(snowflake)


@lru_cache
def get_decision_service() -> DecisionService:
    settings = get_settings()
    return DecisionService(
        engine=DecisionEngine(),
        evidence=SerpApiClient(settings.serpapi_api_key),
        explainer=GeminiClient(settings.gemini_api_key, settings.gemini_model),
    )


def get_guardian_provider_service() -> GuardianProviderService:
    settings = get_settings()
    return GuardianProviderService(
        repository=get_guardian_repository(),
        search=GuardianProviderSearchClient(settings.serpapi_api_key),
        database_path=settings.guardian_database_path,
        ttl_seconds=settings.guardian_provider_cache_ttl_seconds,
    )


def get_guardian_market_service() -> GuardianMarketEvidenceService:
    settings = get_settings()
    return GuardianMarketEvidenceService(
        repository=get_guardian_repository(),
        search=SerpApiClient(settings.serpapi_api_key),
        database_path=settings.guardian_database_path,
        ttl_seconds=settings.guardian_market_cache_ttl_seconds,
    )


def get_guardian_chat_service() -> GuardianChatService:
    settings = get_settings()
    return GuardianChatService(
        repository=get_guardian_repository(),
        provider_service=get_guardian_provider_service(),
        market_service=get_guardian_market_service(),
        gemini=GuardianGeminiClient(
            settings.gemini_api_key,
            settings.guardian_gemini_model or settings.gemini_model,
            timeout=settings.guardian_gemini_timeout_seconds,
            max_output_tokens=settings.guardian_gemini_max_output_tokens,
        ),
    )
