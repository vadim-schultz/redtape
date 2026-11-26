"""Integration tests for LeasedQueue claim ordering with phase and grouping."""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

from app.features.search.leased_queue import LeasedQueue
from app.models.search import EmbeddingTask, WorkTaskStatus
from app.models.translation import TranslationTask

from embedding_support import make_key
from search_support import make_candidate

# ===== SLICE 1: Add phase_field and grouping_field Parameters =====


def test_claim_accepts_phase_and_grouping_parameters(db_session):
    """Happy path: claim() accepts phase_field and grouping_field without TypeError."""
    api_key_id = make_key(db_session).id
    candidate_id = make_candidate(db_session).id
    now = datetime.utcnow()

    # Create a task to claim
    task = TranslationTask(
        id=uuid4(),
        candidate_id=candidate_id,
        source_hash="test-hash",
        locale="en",
        status=WorkTaskStatus.PENDING,
        priority=10,
        phase=1,
        created_at=now,
    )
    db_session.add(task)
    db_session.commit()

    # Claim with phase_field and grouping_field
    queue = LeasedQueue(db_session, TranslationTask)
    claimed = queue.claim(
        api_key_id=api_key_id,
        now=now,
        limit=1,
        scope=[],
        phase_field=TranslationTask.phase,
        grouping=(TranslationTask.candidate_id,),
    )

    # Assert claim succeeded and returned the task
    assert len(claimed) == 1
    assert claimed[0].id == task.id


def test_claim_backward_compatible_without_phase_or_grouping(db_session):
    """Negative path: claim() works without phase_field and grouping_field (backward compatible)."""
    api_key_id = make_key(db_session).id
    candidate_id = make_candidate(db_session).id
    now = datetime.utcnow()

    # Create a task
    task = TranslationTask(
        id=uuid4(),
        candidate_id=candidate_id,
        source_hash="test-hash",
        locale="en",
        status=WorkTaskStatus.PENDING,
        priority=10,
        phase=1,
        created_at=now,
    )
    db_session.add(task)
    db_session.commit()

    # Claim WITHOUT phase_field or grouping_field
    queue = LeasedQueue(db_session, TranslationTask)
    claimed = queue.claim(
        api_key_id=api_key_id,
        now=now,
        limit=1,
        scope=[],
    )

    # Assert claim succeeded
    assert len(claimed) == 1
    assert claimed[0].id == task.id


# ===== SLICE 2: Verify Phase and Grouping Order in SQL =====


def test_claim_respects_phase_and_grouping_order(db_session):
    """Happy path: Tasks claimed in phase → priority → grouping → created_at → id order."""
    api_key_id = make_key(db_session).id
    # grouping orders candidates by id, so the lower id is the first group
    candidate_id_1, candidate_id_2 = sorted(make_candidate(db_session).id for _ in range(2))
    now = datetime.utcnow()

    # Create tasks with explicit phase and grouping
    t_a1 = TranslationTask(
        id=uuid4(),
        candidate_id=candidate_id_1,
        source_hash="test-hash",
        locale="en",
        status=WorkTaskStatus.PENDING,
        priority=10,
        phase=1,
        created_at=now,
    )
    t_a2 = TranslationTask(
        id=uuid4(),
        candidate_id=candidate_id_1,
        source_hash="test-hash",
        locale="fr",
        status=WorkTaskStatus.PENDING,
        priority=10,
        phase=1,
        created_at=now + timedelta(seconds=1),
    )
    t_b1 = TranslationTask(
        id=uuid4(),
        candidate_id=candidate_id_2,
        source_hash="test-hash",
        locale="en",
        status=WorkTaskStatus.PENDING,
        priority=10,
        phase=1,
        created_at=now,
    )
    t_c1 = TranslationTask(
        id=uuid4(),
        candidate_id=candidate_id_1,
        source_hash="test-hash",
        locale="de",
        status=WorkTaskStatus.PENDING,
        priority=10,
        phase=2,
        created_at=now,
    )

    for task in [t_a1, t_a2, t_b1, t_c1]:
        db_session.add(task)
    db_session.commit()

    # Claim with phase and grouping
    queue = LeasedQueue(db_session, TranslationTask)
    claimed = queue.claim(
        api_key_id=api_key_id,
        now=now,
        limit=4,
        scope=[],
        phase_field=TranslationTask.phase,
        grouping=(TranslationTask.candidate_id,),
    )

    # Assert order: phase 1 (group 1 in order, then group 2), then phase 2
    assert len(claimed) == 4
    assert claimed[0].id == t_a1.id  # phase=1, group=cid_1, created_at=now
    assert claimed[1].id == t_a2.id  # phase=1, group=cid_1, created_at=now+1s
    assert claimed[2].id == t_b1.id  # phase=1, group=cid_2, created_at=now
    assert claimed[3].id == t_c1.id  # phase=2, group=cid_1


def test_claim_without_phase_ignores_phase_in_order(db_session):
    """Negative path: Claim without phase_field uses priority order, ignoring phase."""
    api_key_id = make_key(db_session).id
    # grouping orders candidates by id, so the lower id is the first group
    candidate_id_1, candidate_id_2 = sorted(make_candidate(db_session).id for _ in range(2))
    now = datetime.utcnow()

    # Create tasks: one phase=2 with high priority (low number), one phase=1 with low priority (high number)
    t_phase2_high_priority = TranslationTask(
        id=uuid4(),
        candidate_id=candidate_id_1,
        source_hash="test-hash",
        locale="en",
        status=WorkTaskStatus.PENDING,
        priority=5,  # High priority (low number)
        phase=2,
        created_at=now,
    )
    t_phase1_low_priority = TranslationTask(
        id=uuid4(),
        candidate_id=candidate_id_2,
        source_hash="test-hash",
        locale="en",
        status=WorkTaskStatus.PENDING,
        priority=100,  # Low priority (high number)
        phase=1,
        created_at=now,
    )

    db_session.add(t_phase2_high_priority)
    db_session.add(t_phase1_low_priority)
    db_session.commit()

    # Claim WITHOUT phase_field
    queue = LeasedQueue(db_session, TranslationTask)
    claimed = queue.claim(
        api_key_id=api_key_id,
        now=now,
        limit=2,
        scope=[],
        # Note: no phase_field provided
        grouping=(TranslationTask.candidate_id,),
    )

    # Assert: phase=2 (priority=5) comes before phase=1 (priority=100) because priority order is used
    assert len(claimed) == 2
    assert claimed[0].id == t_phase2_high_priority.id  # priority=5 comes first
    assert claimed[1].id == t_phase1_low_priority.id  # priority=100 comes second


# ===== SLICE 5: Integration Tests (All Pipelines) =====


def test_all_pipelines_respect_phase_and_grouping_order(db_session):
    """Integration: Translation and Embedding pipelines claim in correct phase+grouping order."""
    api_key_id = make_key(db_session).id
    # grouping orders candidates by id, so the lower id is the first group
    candidate_id_1, candidate_id_2 = sorted(make_candidate(db_session).id for _ in range(2))
    now = datetime.utcnow()

    # Enqueue across translation and embedding pipelines
    # Translation: candidate_1 (phase=1), candidate_2 (phase=2)
    trans_c1_p1 = TranslationTask(
        id=uuid4(),
        candidate_id=candidate_id_1,
        source_hash="test-hash",
        locale="en",
        status=WorkTaskStatus.PENDING,
        priority=10,
        phase=1,
        created_at=now,
    )
    trans_c2_p2 = TranslationTask(
        id=uuid4(),
        candidate_id=candidate_id_2,
        source_hash="test-hash",
        locale="en",
        status=WorkTaskStatus.PENDING,
        priority=10,
        phase=2,
        created_at=now,
    )

    # Embedding: candidate_1 (phase=1), candidate_2 (phase=2)
    embed_c1_p1 = EmbeddingTask(
        id=uuid4(),
        candidate_id=candidate_id_1,
        model="test-model",
        locale="en",
        text_hash="hash1",
        status=WorkTaskStatus.PENDING,
        priority=10,
        phase=1,
        created_at=now,
    )
    embed_c2_p2 = EmbeddingTask(
        id=uuid4(),
        candidate_id=candidate_id_2,
        model="test-model",
        locale="en",
        text_hash="hash2",
        status=WorkTaskStatus.PENDING,
        priority=10,
        phase=2,
        created_at=now,
    )

    for task in [trans_c1_p1, trans_c2_p2, embed_c1_p1, embed_c2_p2]:
        db_session.add(task)
    db_session.commit()

    # Claim from translation pipeline
    trans_queue = LeasedQueue(db_session, TranslationTask)
    trans_claimed = trans_queue.claim(
        api_key_id=api_key_id,
        now=now,
        limit=10,
        scope=[],
        phase_field=TranslationTask.phase,
        grouping=(TranslationTask.candidate_id,),
    )

    # Claim from embedding pipeline
    embed_queue = LeasedQueue(db_session, EmbeddingTask)
    embed_claimed = embed_queue.claim(
        api_key_id=api_key_id,
        now=now,
        limit=10,
        scope=[],
        phase_field=EmbeddingTask.phase,
        grouping=(EmbeddingTask.candidate_id,),
    )

    # Assert ordering within each pipeline
    assert len(trans_claimed) == 2
    assert trans_claimed[0].id == trans_c1_p1.id  # phase=1 first
    assert trans_claimed[1].id == trans_c2_p2.id  # phase=2 second

    assert len(embed_claimed) == 2
    assert embed_claimed[0].id == embed_c1_p1.id  # phase=1 first
    assert embed_claimed[1].id == embed_c2_p2.id  # phase=2 second


def test_claim_backward_compatible_without_phase_field(db_session):
    """Negative path: Existing code without phase/grouping still works."""
    api_key_id = make_key(db_session).id
    candidate_id = make_candidate(db_session).id
    now = datetime.utcnow()

    task = TranslationTask(
        id=uuid4(),
        candidate_id=candidate_id,
        source_hash="test-hash",
        locale="en",
        status=WorkTaskStatus.PENDING,
        priority=10,
        phase=1,
        created_at=now,
    )
    db_session.add(task)
    db_session.commit()

    queue = LeasedQueue(db_session, TranslationTask)

    # Call without phase_field or grouping_field (backward compat)
    claimed = queue.claim(
        api_key_id=api_key_id,
        now=now,
        limit=1,
        scope=[],
        # No phase_field, no grouping_field
    )

    assert len(claimed) == 1
    assert claimed[0].id == task.id
