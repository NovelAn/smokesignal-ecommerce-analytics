"""MiniMax-first orchestration for AI Analysis V2."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, Callable, Literal

from backend.ai.analysis_errors import AIAnalysisUnavailableError
from .preprocessing import MessageWindow, prepare_windows
from .prompt import build_analysis_prompt
from .rollup import build_customer_state
from .schemas import AnalysisPayload, CustomerState, validate_model_payload

if TYPE_CHECKING:
    from .repository import AIAnalysisV2Repository


@dataclass(frozen=True)
class AnalyzedWindow:
    payload: AnalysisPayload
    provider: str
    model: str


@dataclass(frozen=True)
class AnalysisRunResult:
    buyer_nick: str
    status: Literal["completed", "skipped"]
    provider: str
    payloads: tuple[AnalysisPayload, ...]
    customer_state: CustomerState | dict[str, Any] | None
    reason: str | None = None


class AIAnalysisV2Analyzer:
    PROMPT_VERSION = "ai-analysis-v2.0"

    def __init__(
        self,
        repository: AIAnalysisV2Repository | None = None,
        minimax: Any | None = None,
        deepseek: Any | None = None,
        clock: Callable[[], datetime] = datetime.now,
    ):
        if repository is None:
            from .repository import AIAnalysisV2Repository

            repository = AIAnalysisV2Repository()
        if minimax is None:
            from backend.ai.minimax_client import MiniMaxClient

            minimax = MiniMaxClient()
        self.repository = repository
        self.minimax = minimax
        self.deepseek = deepseek
        self.clock = clock

    def analyze_buyer(
        self,
        buyer_nick: str,
        mode: Literal["full", "incremental"] = "incremental",
    ) -> AnalysisRunResult:
        source = self.repository.load_source(buyer_nick, mode)
        windows = prepare_windows(
            buyer_nick,
            source.chats,
            source.checkpoint,
            prompt_version=self.PROMPT_VERSION,
        )
        if not windows:
            return AnalysisRunResult(
                buyer_nick, "skipped", "cache", (), source.customer_state, "no_new_messages"
            )

        payloads: list[AnalysisPayload] = []
        last_provider = "cache"
        for window in windows:
            completed = self.repository.find_completed_run(
                buyer_nick, window.fingerprint, self.PROMPT_VERSION
            )
            if completed:
                payloads.append(completed.payload)
                last_provider = completed.provider or last_provider
                continue

            run_id = self.repository.start_run(
                buyer_nick,
                mode,
                window,
                self.PROMPT_VERSION,
                provider="minimax",
                model=getattr(self.minimax, "model", None),
            )
            try:
                analyzed = self._analyze_window(
                    window, source.open_events, source.profile, source.customer_state
                )
                state = build_customer_state(
                    self.repository.events_for_rollup(buyer_nick, analyzed.payload),
                    now=self.clock(),
                    buyer_nick=buyer_nick,
                    last_run_id=run_id,
                )
                self.repository.persist_success(
                    run_id=run_id,
                    buyer_nick=buyer_nick,
                    window=window,
                    payload=analyzed.payload,
                    state=state,
                    provider=analyzed.provider,
                    model=analyzed.model,
                )
                payloads.append(analyzed.payload)
                last_provider = analyzed.provider
            except Exception as error:
                self.repository.persist_failure(
                    run_id, type(error).__name__, str(error)
                )
                raise AIAnalysisUnavailableError(
                    "AI Analysis V2 failed; retry later"
                ) from error

        current = self.repository.get_buyer_analysis(buyer_nick).customer_state
        return AnalysisRunResult(
            buyer_nick,
            "completed",
            last_provider,
            tuple(payloads),
            current,
        )

    def _analyze_window(
        self,
        window: MessageWindow,
        open_events: list[dict[str, Any]],
        profile: dict[str, Any],
        customer_state: CustomerState | dict[str, Any] | None,
    ) -> AnalyzedWindow:
        prompt = build_analysis_prompt(window, open_events)
        last_error: Exception | None = None
        for _ in range(2):
            try:
                payload = validate_model_payload(self.minimax.analyze_v2(prompt))
                return AnalyzedWindow(
                    payload, "minimax", getattr(self.minimax, "model", "MiniMax-M3")
                )
            except Exception as error:
                last_error = error

        if self._allow_deepseek(profile, customer_state):
            deepseek = self._get_deepseek()
            try:
                payload = validate_model_payload(deepseek.analyze_v2(prompt))
                return AnalyzedWindow(
                    payload,
                    "deepseek",
                    getattr(deepseek, "model_chat", "deepseek-v4-flash"),
                )
            except Exception as error:
                last_error = error

        raise last_error or RuntimeError("no AI provider available")

    def _get_deepseek(self) -> Any:
        if self.deepseek is None:
            from backend.ai.deepseek_client import DeepSeekClient

            self.deepseek = DeepSeekClient()
        return self.deepseek

    @staticmethod
    def _allow_deepseek(
        profile: dict[str, Any],
        customer_state: CustomerState | dict[str, Any] | None,
    ) -> bool:
        tag = str(profile.get("client_monthly_tag") or "").upper()
        if tag in {"V2", "V3"}:
            return True
        if isinstance(customer_state, CustomerState):
            priority = customer_state.attention_priority
            sentiment = customer_state.current_sentiment_label
        else:
            state = customer_state or {}
            priority = state.get("attention_priority")
            sentiment = state.get("current_sentiment_label")
        return priority in {"urgent", "high"} or sentiment == "Negative"
