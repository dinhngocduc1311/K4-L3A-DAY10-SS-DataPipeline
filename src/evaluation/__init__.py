from .testset import BenchmarkTestSet, build_test_set, load_or_create_test_set


def __getattr__(name: str):
    if name in {"EvaluationBundle", "JudgeVerdict", "evaluate_pipeline"}:
        from . import metrics

        return getattr(metrics, name)
    raise AttributeError(name)
