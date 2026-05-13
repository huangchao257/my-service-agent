from app.core.memory_manager import MemoryManager


def test_memory_manager_init():
    mm = MemoryManager()
    assert mm is not None


def test_cosine_similarity_identical():
    mm = MemoryManager()
    v = [1.0, 2.0, 3.0]
    score = mm._cosine_similarity(v, v)
    assert abs(score - 1.0) < 0.001


def test_cosine_similarity_orthogonal():
    mm = MemoryManager()
    score = mm._cosine_similarity([1.0, 0.0], [0.0, 1.0])
    assert abs(score) < 0.001


def test_cosine_similarity_empty():
    mm = MemoryManager()
    score = mm._cosine_similarity([], [])
    assert score == 0.0