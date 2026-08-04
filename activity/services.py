from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from django.contrib.auth.models import User
from django.db.models import Count, Min

from .models import PageEngagement

VISIT = 'visit'


@dataclass
class SessionSummary:
    """One row in the session picker: an at-a-glance summary of a whole browsing session."""

    session_key: str
    user: Optional[User]
    started_at: datetime
    start_url: str
    page_count: int
    interaction_count: int


@dataclass
class SessionStep:
    """One entry in a session's ordered step list - a page visit, click, or input."""

    kind: str  # VISIT, ElementInteraction.CLICK, or ElementInteraction.INPUT
    occurred_at: datetime
    url: str
    xpath: Optional[str] = None
    value: Optional[str] = None


def list_sessions():
    """List recorded sessions, most recently started first.

    Returns:
        A list of `SessionSummary`, one per distinct session_key.
    """
    rows = (
        PageEngagement.objects.exclude(session_key__isnull=True)
        .values('session_key')
        .annotate(
            started_at=Min('started_at'),
            page_count=Count('id', distinct=True),
            interaction_count=Count('interactions', distinct=True),
        )
        .order_by('-started_at')
    )

    summaries = []
    for row in rows:
        # user and start_url aren't meaningfully aggregatable (user should be consistent across
        # a session in practice) - look both up from that session's earliest engagement instead.
        first = (
            PageEngagement.objects.filter(session_key=row['session_key'])
            .select_related('user')
            .order_by('started_at')
            .first()
        )
        summaries.append(
            SessionSummary(
                session_key=row['session_key'],
                user=first.user if first else None,
                started_at=row['started_at'],
                start_url=first.url if first else '',
                page_count=row['page_count'],
                interaction_count=row['interaction_count'],
            )
        )
    return summaries


def get_session_steps(session_key):
    """Build the ordered step list for one session, across every page it visited.

    A page-visit "step" is synthesized for each `PageEngagement`, interleaved with its real
    `ElementInteraction` steps, and the whole thing is sorted by timestamp - not just
    concatenated per visit - since two concurrent tabs in the same session produce two
    `PageEngagement`s whose events can interleave in wall-clock time.

    Args:
        session_key: The session to build the timeline for.

    Returns:
        A list of `SessionStep`, oldest first.
    """
    engagements = PageEngagement.objects.filter(session_key=session_key).prefetch_related('interactions')

    steps = []
    for engagement in engagements:
        steps.append(SessionStep(kind=VISIT, occurred_at=engagement.started_at, url=engagement.url))
        for interaction in engagement.interactions.all():
            steps.append(
                SessionStep(
                    kind=interaction.event_type,
                    occurred_at=interaction.occurred_at,
                    url=engagement.url,
                    xpath=interaction.xpath,
                    value=interaction.value,
                )
            )

    steps.sort(key=lambda step: step.occurred_at)
    return steps
