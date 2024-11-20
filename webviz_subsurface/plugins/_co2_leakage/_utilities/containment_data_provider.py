from typing import List, Union

import pandas as pd

from webviz_subsurface._providers import EnsembleTableProvider
from webviz_subsurface.plugins._co2_leakage._utilities.generic import (
    Co2MassScale,
    Co2VolumeScale,
    MenuOptions,
)


class ContainmentDataValidationError(Exception):
    pass


class ContainmentDataProvider:
    def __init__(self, table_provider: EnsembleTableProvider):
        ContainmentDataProvider._validate(table_provider)
        self._provider = table_provider
        self._menu_options = ContainmentDataProvider._get_menu_options(self._provider)

    @property
    def menu_options(self) -> MenuOptions:
        return self._menu_options

    @property
    def realizations(self) -> List[int]:
        return self._provider.realizations()

    def extract_dataframe(
        self, realization: int, scale: Union[Co2MassScale, Co2VolumeScale]
    ) -> pd.DataFrame:
        df = self._provider.get_column_data(
            self._provider.column_names(), [realization]
        )
        scale_factor = self._find_scale_factor(scale)
        if scale_factor == 1.0:
            return df
        df["amount"] /= scale_factor
        return df

    def extract_condensed_dataframe(
        self,
        co2_scale: Union[Co2MassScale, Co2VolumeScale],
    ) -> pd.DataFrame:
        df = self._provider.get_column_data(self._provider.column_names())
        df = df.loc[(df["zone"] == "all") & (df["region"] == "all") & (df["plume_group"] == "all")]
        if co2_scale == Co2MassScale.MTONS:
            df.loc[:, "amount"] /= 1e9
        elif co2_scale == Co2MassScale.NORMALIZE:
            df.loc[:, "amount"] /= df["amount"].max()
        return df

    def _find_scale_factor(
        self,
        scale: Union[Co2MassScale, Co2VolumeScale],
    ) -> float:
        if scale == Co2MassScale.KG:
            return 0.001
        if scale in (Co2MassScale.TONS, Co2VolumeScale.CUBIC_METERS):
            return 1.0
        if scale == Co2MassScale.MTONS:
            return 1e6
        if scale == Co2VolumeScale.BILLION_CUBIC_METERS:
            return 1e9
        if scale in (Co2MassScale.NORMALIZE, Co2VolumeScale.NORMALIZE):
            df = self._provider.get_column_data(["amount"])
            return df["amount"].max()
        return 1.0

    @staticmethod
    def _get_menu_options(provider: EnsembleTableProvider) -> MenuOptions:
        col_names = provider.column_names()
        realization = provider.realizations()[0]
        df = provider.get_column_data(col_names, [realization])
        zones = ["all"]
        for zone in list(df["zone"]):
            if zone not in zones:
                zones.append(zone)
        regions = ["all"]
        for region in list(df["region"]):
            if region not in regions:
                regions.append(region)
        plume_groups = ["all"]
        for plume_group in list(df["plume_group"]):
            if plume_group not in plume_groups:
                plume_groups.append(plume_group)
        if "free_gas" in list(df["phase"]):
            phases = ["total", "free_gas", "trapped_gas", "aqueous"]
        else:
            phases = ["total", "gas", "aqueous"]
        return {
            "zones": zones if len(zones) > 1 else [],
            "regions": regions if len(regions) > 1 else [],
            "phases": phases,
            "plume_groups": plume_groups,
        }

    @staticmethod
    def _validate(provider: EnsembleTableProvider) -> None:
        col_names = provider.column_names()
        required_columns = ["date", "amount", "phase", "containment", "zone", "region", "plume_group"]
        missing_columns = [col for col in required_columns if col not in col_names]
        realization = provider.realizations()[0]
        if len(missing_columns) == 0:
            return
        raise ContainmentDataValidationError(
            f"EnsembleTableProvider validation error for provider {provider} in "
            f"realization {realization} (and possibly other csv-files).\n"
            f"  Expected columns: {', '.join(missing_columns)}\n"
            f"  Found columns: {', '.join(col_names)}\n"
            f"  (Missing columns: {', '.join(missing_columns)})"
            f"Provided files are possibly from an outdated version of ccs-scripts?"
        )
