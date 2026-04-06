import math

import numpy
import pandas


def provides(*, depends):
    """
    Declares column dependencies and optional per-column ingest transforms.

    Forms:
      - @provides(depends=None) or @provides(depends=[])
      - @provides(depends="x")
      - @provides(depends=["x", "y"])
      - @provides(depends={"x": callable, "y": callable})

    Dict form:
      - Keys are dependency column names.
      - Values are callables(series) -> ingested value.
    """
    if depends is None:
        dependencies = tuple()
        ingest_map = {}
    elif isinstance(depends, str):
        dependencies = (depends,)
        ingest_map = {}
    elif isinstance(depends, dict):
        dependencies = tuple(depends.keys())
        ingest_map = dict(depends)
    else:
        dependencies = tuple(depends)
        ingest_map = {}

    def decorator(method):
        setattr(
            method,
            "_provides_spec",
            {"dependencies": dependencies, "ingest_map": ingest_map},
        )
        return method

    return decorator


class Protocol:
    """
    Abstract pipeline superclass.

    Subclasses provide @provides-decorated transformer methods (typically via mixins).
    Each transformer method returns a pandas.DataFrame whose columns are merged into
    the running state dataframe.

    Dependency ordering uses:
      - produced columns: transformer method names
      - required columns: values in @provides(depends=...)
    """

    def __init__(self, sphere_radius, refractive_index=1.0):
        if sphere_radius <= 0:
            raise ValueError("sphere_radius must be > 0.")
        if refractive_index <= 0:
            raise ValueError("refractive_index must be > 0.")

        self.sphere_radius = float(sphere_radius)
        self.refractive_index = float(refractive_index)

    @property
    def provided(self):
        # Exposes currently prepared dependency values for the active transformer.
        provided = getattr(self, "_current_provided", None)
        if provided is None:
            return {}
        return provided

    def __call__(self, frame):
        if ("x" not in frame.columns) or ("y" not in frame.columns):
            raise ValueError("frame must include 'x' and 'y' columns.")

        state_frame = frame.copy()

        transformers = self._collect_transformers()
        execution_order = self._topological_order(
            transformers=transformers, available_columns=set(state_frame.columns)
        )

        for transformer_name in execution_order:
            payload = transformers[transformer_name]
            method = payload["method"]

            self._current_provided = self._prepare_provided(
                state_frame=state_frame,
                dependencies=payload["dependencies"],
                ingest_map=payload["ingest_map"],
            )

            result_frame = method(state_frame)

            if not isinstance(result_frame, pandas.DataFrame):
                raise TypeError(
                    f"Transformer '{transformer_name}' must return pandas.DataFrame, got {type(result_frame)!r}."
                )

            if not result_frame.index.equals(state_frame.index):
                raise ValueError(
                    f"Transformer '{transformer_name}' returns misaligned index."
                )

            for column_name in result_frame.columns:
                state_frame[column_name] = result_frame[column_name]

        self._current_provided = None
        return state_frame

    def _prepare_provided(self, *, state_frame, dependencies, ingest_map):
        # Prepares per-dependency values, optionally applying ingest transforms.
        provided = {}
        for column_name in dependencies:
            series = state_frame[column_name]
            transform = ingest_map.get(column_name)
            provided[column_name] = (
                transform(series) if transform is not None else series
            )
        return provided

    def _collect_transformers(self):
        # Discovers transformer methods via @provides metadata.
        transformers = {}
        for attribute_name in dir(self):
            attribute = getattr(self, attribute_name, None)
            if not callable(attribute):
                continue

            provides_spec = getattr(attribute, "_provides_spec", None)
            if provides_spec is None:
                continue

            transformers[attribute.__name__] = {
                "dependencies": tuple(provides_spec["dependencies"]),
                "ingest_map": dict(provides_spec["ingest_map"]),
                "method": attribute,
            }

        return transformers

    def _topological_order(self, transformers, available_columns):
        # Builds dependency graph over transformer outputs and performs Kahn topological sort.
        transformer_names = set(transformers.keys())

        missing_dependencies = {}
        for node_name, payload in transformers.items():
            dependencies = payload["dependencies"]
            missing = [
                dep
                for dep in dependencies
                if (dep not in transformer_names) and (dep not in available_columns)
            ]
            if missing:
                missing_dependencies[node_name] = missing

        if missing_dependencies:
            details = "; ".join(
                f"{name}: {deps}" for name, deps in sorted(missing_dependencies.items())
            )
            raise ValueError(f"Missing dependencies for transformers: {details}")

        adjacency = {name: set() for name in transformer_names}
        indegree = {name: 0 for name in transformer_names}

        for node_name, payload in transformers.items():
            dependencies = payload["dependencies"]
            for dep in dependencies:
                if dep in transformer_names:
                    adjacency[dep].add(node_name)
                    indegree[node_name] += 1

        ready = sorted([name for name, degree in indegree.items() if degree == 0])
        ordered = []

        while ready:
            current = ready.pop(0)
            ordered.append(current)

            for neighbor in sorted(adjacency[current]):
                indegree[neighbor] -= 1
                if indegree[neighbor] == 0:
                    ready.append(neighbor)
                    ready.sort()

        if len(ordered) != len(transformer_names):
            remaining = sorted(
                [name for name, degree in indegree.items() if degree > 0]
            )
            raise ValueError(
                f"Dependency cycle detected among transformers: {remaining}"
            )

        return ordered
