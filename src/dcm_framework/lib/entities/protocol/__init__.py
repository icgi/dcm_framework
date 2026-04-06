import functools
import graphlib
import pandas

def contract(provides=None, requires=None):
    """ Declares which protocol columns a __call__ method requires and provides. """

    def decorator(method):
        method.provides = provides or []
        method.requires = requires or []

        @functools.wraps(method)
        def wrapper(self, protocol, manifest, *args, **kwargs):
            missing = [
                column for column in method.requires
                if column not in protocol.columns
            ]
            if missing:
                raise KeyError(
                    f"{self.__class__.__name__} requires missing columns: {missing}"
                )

            protocol, manifest = method(self, protocol, manifest, *args, **kwargs)
            result = protocol, manifest
            return result

        wrapper.provides = method.provides
        wrapper.requires = method.requires

        return wrapper

    return decorator


class Protocol:
    """ Base class for protocol assembly. Resolves execution order from contract metadata. """

    def _collect_transformers(self):
        """ Collects mixin base classes whose __call__ carries a contract decorator. """
        result = [
            base for base in type(self).__mro__
            if base not in (type(self), Protocol, object)
            and hasattr(getattr(base, "__call__", None), "provides")
        ]
        return result

    def _resolve_execution_order(self, transformer_classes):
        """ Topological sort of transformer classes. Uses MRO position as tiebreaker for unconstrained nodes. """
        result = None

        mro_position = {
            transformer_class: index
            for index, transformer_class in enumerate(transformer_classes)
        }

        provider_index = {}
        for transformer_class in transformer_classes:
            call_method = transformer_class.__call__
            for column in call_method.provides:
                provider_index[column] = transformer_class

        dependencies = {}
        for transformer_class in transformer_classes:
            call_method = transformer_class.__call__
            dependencies[transformer_class] = {
                provider_index[column]
                for column in call_method.requires
                if column in provider_index
            }

        # chains unconstrained transformers to their MRO predecessor
        sorted_by_mro = sorted(transformer_classes, key=lambda transformer_class: mro_position[transformer_class])
        for index, transformer_class in enumerate(sorted_by_mro):
            if index == 0:
                continue
            call_method = transformer_class.__call__
            has_contract_edges = call_method.requires or call_method.provides
            if not has_contract_edges:
                predecessor = sorted_by_mro[index - 1]
                dependencies[transformer_class].add(predecessor)

        sorter = graphlib.TopologicalSorter(dependencies)
        result = list(sorter.static_order())
        return result

    def build(self, initial_frame=None, manifest=None):
        """ Executes all contract-decorated transformers in dependency order. """
        protocol = initial_frame if initial_frame is not None else pandas.DataFrame()
        manifest = manifest if manifest is not None else {}

        transformer_classes = self._collect_transformers()
        execution_order = self._resolve_execution_order(transformer_classes)

        for transformer_class in execution_order:
            print(transformer_class.__name__)
            call_method = transformer_class.__call__
            protocol, manifest = call_method(self, protocol, manifest)

        result = protocol, manifest
        return result