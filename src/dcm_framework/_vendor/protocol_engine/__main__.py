import pandas
import fire
import time

from . import contract
from mixins import VerboseProtocol


class SampleSeeder:
    """ Seeds the protocol with sample identifiers under the 'identity' group. """

    @contract(provides=[("identity", "sample_id")])
    def __call__(self, protocol, manifest):
        protocol = pandas.DataFrame(
            [["S1"], ["S2"], ["S3"]],
            columns=pandas.MultiIndex.from_tuples([("identity", "sample_id")]),
        )
        manifest["seeded_count"] = len(protocol)
        result = protocol, manifest

        time.sleep(3)

        return result


class VolumeAssigner:
    """ Assigns a working volume under the 'inputs' group. """

    @contract(
        provides=[("inputs", "volume_ul")],
        requires=[("identity", "sample_id")],
    )
    def __call__(self, protocol, manifest):
        protocol = protocol.copy()
        protocol[("inputs", "volume_ul")] = [50.0, 75.0, 100.0]
        result = protocol, manifest

        time.sleep(3)

        return result


class ConcentrationAssigner:
    """ Assigns a stock concentration under the 'inputs' group. """

    @contract(
        provides=[("inputs", "concentration_ng_ul")],
        requires=[("identity", "sample_id")],
    )
    def __call__(self, protocol, manifest):
        protocol = protocol.copy()
        protocol[("inputs", "concentration_ng_ul")] = [20.0, 40.0, 10.0]
        result = protocol, manifest

        time.sleep(3)

        return result


class MassCalculator:
    """ Computes total mass and stores it under the 'derived' group. """

    @contract(
        provides=[("derived", "mass_ng")],
        requires=[("inputs", "volume_ul"), ("inputs", "concentration_ng_ul")],
    )
    def __call__(self, protocol, manifest):
        protocol = protocol.copy()
        protocol[("derived", "mass_ng")] = (
            protocol[("inputs", "volume_ul")]
            * protocol[("inputs", "concentration_ng_ul")]
        )
        result = protocol, manifest

        time.sleep(3)

        return result


class MassCategorizer:
    """ Per-row classifier that tags each sample as 'low', 'medium', or 'high' mass. """

    @contract(
        provides=[("derived", "mass_category")],
        requires=[("derived", "mass_ng")],
        level="entry",
    )
    def __call__(self, entry, manifest):
        # entry-level transformers receive one row at a time and a read-only manifest;
        # the engine dispatches all rows concurrently through Protocol.apply and joins
        # the per-row results back onto the protocol by index
        mass_ng = entry[("derived", "mass_ng")]
        if mass_ng < 1000.0:
            category = "low"
        elif mass_ng < 2500.0:
            category = "medium"
        else:
            category = "high"

        time.sleep(3)

        result = {("derived", "mass_category"): category}
        return result


class DilutionPlanner:
    """ Plans diluent volume and stores it under the 'plan' group. """

    @contract(
        provides=[("plan", "diluent_ul")],
        requires=[("derived", "mass_ng")],
    )
    def __call__(self, protocol, manifest):
        target_mass = 500.0
        manifest["target_mass_ng"] = target_mass
        protocol = protocol.copy()
        protocol[("plan", "diluent_ul")] = (
            protocol[("derived", "mass_ng")] - target_mass
        ).clip(lower=0.0)
        result = protocol, manifest

        time.sleep(3)

        return result


class ManifestStamper:
    """ Records group/column summary in the manifest after the frame is populated. """

    @contract()
    def __call__(self, protocol, manifest):
        manifest["row_count"] = len(protocol)
        manifest["groups"] = sorted({group for group, _ in protocol.columns})
        manifest["columns"] = list(protocol.columns)
        result = protocol, manifest
        return result


class SamplePrepProtocol(
    SampleSeeder,
    VolumeAssigner,
    ConcentrationAssigner,
    MassCalculator,
    MassCategorizer,
    DilutionPlanner,
    ManifestStamper,
    #
    VerboseProtocol,
):
    """ Concrete protocol composed of the transformer mixins above. """


def main():
    """ Builds the SamplePrepProtocol and prints the resulting frame and manifest. """

    protocol, manifest = SamplePrepProtocol().build()
    print(protocol)
    print()
    print(manifest)


if __name__ == "__main__":
    fire.Fire(main)
