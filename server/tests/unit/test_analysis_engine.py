"""Unit tests for analysis engine."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_run_analysis_uses_fallback_chain():
    """Analysis should pass all providers ordered by fallback_order to orchestrator."""
    mock_db = AsyncMock()

    with patch("app.core.analysis_engine.AsyncSession") as mock_session_cls, \
         patch("app.core.analysis_engine.EnvironmentRepository") as mock_env_repo_cls, \
         patch("app.core.analysis_engine.AIProviderRepository") as mock_provider_repo_cls, \
         patch("app.core.analysis_engine.AnalysisRepository") as mock_analysis_repo_cls, \
         patch("app.core.analysis_engine.MCPClient") as mock_mcp_cls, \
         patch("app.core.analysis_engine.AgentExecutor") as mock_executor_cls, \
         patch("app.core.analysis_engine.RecommendationEngine") as mock_rec_cls, \
         patch("app.core.analysis_engine.get_plugin") as mock_plugin:

        mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=None)

        mock_analysis = MagicMock(
            id=1,
            environment_id=1,
            ai_provider_id=1,
            analysis_type="performance",
            time_range_hours=24,
            parameters={},
        )
        mock_analysis_repo = mock_analysis_repo_cls.return_value
        mock_analysis_repo.get_by_id = AsyncMock(return_value=mock_analysis)
        mock_analysis_repo.update_status = AsyncMock()

        mock_env = MagicMock(url="https://test.live.dynatrace.com", env_type="saas")
        mock_env_repo = mock_env_repo_cls.return_value
        mock_env_repo.get_by_id = AsyncMock(return_value=mock_env)
        mock_env_repo.get_token = MagicMock(return_value="token")

        provider_a = MagicMock(
            provider_type="anthropic",
            model="claude-sonnet-4-6",
            endpoint=None,
            extra_config={},
        )
        provider_b = MagicMock(
            provider_type="openai",
            model="gpt-4o",
            endpoint=None,
            extra_config={},
        )
        mock_provider_repo = mock_provider_repo_cls.return_value
        mock_provider_repo.get_fallback_chain = AsyncMock(return_value=[provider_a, provider_b])
        mock_provider_repo.get_api_key = MagicMock(return_value="key")

        mock_plugin.return_value.build_prompts.return_value = ("system", "user")

        mock_mcp = mock_mcp_cls.return_value
        mock_mcp.connect = AsyncMock()
        mock_mcp.is_connected = MagicMock(return_value=False)
        mock_mcp_cls.get_from_pool = AsyncMock(return_value=mock_mcp)

        mock_executor = mock_executor_cls.return_value
        mock_executor.run = AsyncMock(
            return_value=MagicMock(final_answer="done", reasoning_steps=[], raw_data=[])
        )

        mock_rec = mock_rec_cls.return_value
        mock_rec.generate = AsyncMock(return_value=[])

        from app.core.analysis_engine import run_analysis

        await run_analysis(1)

        mock_executor_cls.assert_called_once()
        orchestrator = mock_executor_cls.call_args.kwargs["orchestrator"]
        assert len(orchestrator.providers) == 2
        assert orchestrator.providers[0].model == "claude-sonnet-4-6"
        assert orchestrator.providers[1].model == "gpt-4o"
