
from ihydrocal.core.converter import (
    write_stf_day_obd_from_usgs,
    gpkg_attribute_table_to_csv,
)

def write_stf_day_obd_from_usgs_test():
    write_stf_day_obd_from_usgs(
        usgs_csv=r"C:\Users\seonggpa\Documents\projects\watersheds\Pecos\Analysis\calibration\TxtInOut_v02\data_dailyvalues_Pecos.csv",
        output_csv=r"C:\Users\seonggpa\Documents\projects\watersheds\Pecos\Analysis\calibration\TxtInOut_v02\stf_day.obd.csv",
    )

def gpkg_attribute_table_to_csv_test():
    gpkg_attribute_table_to_csv(
        gpkg_path=r"C:\Users\seonggpa\Documents\projects\watersheds\Pecos\gis_shared\channels_gages.gpkg",
        csv_path=r"C:\Users\seonggpa\Documents\projects\watersheds\Pecos\Analysis\calibration\channels_gages.csv",
    )

if __name__ == "__main__":
    gpkg_attribute_table_to_csv_test()