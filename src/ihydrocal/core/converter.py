from pathlib import Path
import pandas as pd


def write_stf_day_obd_from_usgs(
    usgs_csv,
    output_csv="stf_day.obd.csv",
    date_col="Date",
    site_col="site_no",
    flow_col="Q_cms",
    site_prefix="site_",
    decimals=3,
):
    """
    Convert USGS observed daily flow data from long format to wide format.

    Output format:
        date, site_08379500, site_08382000, ...
    """

    usgs_csv = Path(usgs_csv)
    output_csv = Path(output_csv)

    df = pd.read_csv(
        usgs_csv,
        na_values=["NA", "", -999, -99],
        dtype={site_col: str},
    )

    # Keep only required columns
    df = df[[date_col, site_col, flow_col]].copy()

    # Clean date
    df[date_col] = pd.to_datetime(df[date_col])

    # Clean and pad USGS site number
    df[site_col] = (
        df[site_col]
        .astype(str)
        .str.strip()
        .str.replace(".0", "", regex=False)
        .str.zfill(8)
    )

    # Convert flow to numeric
    df[flow_col] = pd.to_numeric(df[flow_col], errors="coerce")

    # Long to wide
    wide = df.pivot_table(
        index=date_col,
        columns=site_col,
        values=flow_col,
        aggfunc="mean",
    )

    # Rename columns: 08379500 -> site_08379500
    wide.columns = [f"{site_prefix}{site}" for site in wide.columns]

    if decimals is not None:
        df[flow_col] = df[flow_col].round(decimals)

    wide = wide.reset_index()
    wide = wide.rename(columns={date_col: "date"})
    wide = wide.sort_values("date")

    if decimals is None:
        wide.to_csv(output_csv, index=False)
    else:
        wide.to_csv(output_csv, index=False, float_format=f"%.{decimals}f")
    return wide


from pathlib import Path
import geopandas as gpd


def gpkg_attribute_table_to_csv(
    gpkg_path,
    csv_path=None,
    layer=None,
    drop_geometry=True,
):
    """
    Convert a GeoPackage layer attribute table to a CSV file.

    Parameters
    ----------
    gpkg_path : str or Path
        Path to the input GeoPackage file, e.g., "gages_checked.gpkg".

    csv_path : str or Path, optional
        Path to the output CSV file. If None, it creates a CSV with the
        same name as the GeoPackage.

    layer : str, optional
        Layer name inside the GeoPackage. If None, GeoPandas will try to
        read the default layer. If your GeoPackage has multiple layers,
        specify the layer name.

    drop_geometry : bool, default=True
        If True, remove the geometry column and export only attributes.

    Returns
    -------
    pandas.DataFrame
        The exported attribute table.
    """

    gpkg_path = Path(gpkg_path)

    if csv_path is None:
        csv_path = gpkg_path.with_suffix(".csv")
    else:
        csv_path = Path(csv_path)

    # Read GeoPackage
    if layer is None:
        gdf = gpd.read_file(gpkg_path)
    else:
        gdf = gpd.read_file(gpkg_path, layer=layer)

    # Remove geometry column if you only want the attribute table
    if drop_geometry:
        df = gdf.drop(columns=gdf.geometry.name)
    else:
        df = gdf.copy()

    # Export to CSV
    df.to_csv(csv_path, index=False)

    print(f"CSV exported: {csv_path}")
    print(f"Number of rows: {len(df)}")
    print(f"Number of columns: {len(df.columns)}")

    return df