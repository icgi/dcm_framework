import pandas
import pathlib

from . import Protocol

class VerboseProtocol(Protocol):
    """

        Protocol enhancement mixin that persists (protocol, manifest) to CSV after every transformer.

        Files are written to ``intermediate_state_directory`` as
        ``protocol___<ordinal>___<TransformerName>.csv`` and
        ``manifest___<ordinal>___<TransformerName>.csv``.

        Defines no ``__call__`` so the engine never mistakes this mixin for a pipeline step;
        this is the convention every protocol enhancement mixin must follow.

    """

    intermediate_state_directory = None
    ordinal_format = "04d"

    def before_protocol_execution(self, protocol, manifest):
        """

            Resolves the intermediate-state directory under the workspace and ensures it exists.

        """

        if self.intermediate_state_directory is None:
            self.intermediate_state_directory = self.workspace / "intermediate"

        intermediate_state_directory = pathlib.Path(self.intermediate_state_directory)
        intermediate_state_directory.mkdir(parents=True, exist_ok=True)

        result = super().before_protocol_execution(protocol, manifest)
        return result

    def after_transformation(self, ordinal, transformer_class, protocol, manifest):
        """

            Writes the intermediate (protocol, manifest) state to disk after the base callback runs.

        """

        protocol, manifest = super().after_transformation(ordinal, transformer_class, protocol, manifest)
        self.write_intermediate_state(protocol, manifest, ordinal, transformer_class.__name__)

        result = protocol, manifest
        return result

    def write_intermediate_state(self, protocol, manifest, ordinal, transformer_name):
        """

            Writes the paired intermediate-state CSVs ``protocol___<ordinal>___<name>.csv`` and
            ``manifest___<ordinal>___<name>.csv`` to ``intermediate_state_directory``.

        """

        # zero-padded ordinal keeps directory listings in execution order
        ordinal_token = format(ordinal, self.ordinal_format)
        intermediate_state_directory = pathlib.Path(self.intermediate_state_directory)

        protocol_path = intermediate_state_directory / f"protocol___{ordinal_token}___{transformer_name}.csv"
        manifest_path = intermediate_state_directory / f"manifest___{ordinal_token}___{transformer_name}.csv"

        # to_csv handles MultiIndex columns natively by emitting multi-row headers
        protocol.to_csv(protocol_path, index=False)

        # split two-level tuple manifest keys into (group, name) columns for human-readable diffs
        records = []
        for key, value in manifest.items():
            if isinstance(key, tuple) and len(key) == 2:
                group, name = key
            else:
                group, name = "", key
            records.append({"group": group, "name": name, "value": value})
        manifest_frame = pandas.DataFrame(records, columns=["group", "name", "value"])
        manifest_frame.to_csv(manifest_path, index=False)