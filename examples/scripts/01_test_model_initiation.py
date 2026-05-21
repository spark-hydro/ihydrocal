import os
# from turtle import pd
import pandas as pd
import ihydrocal as ihc


# def main():
#     print("iHydroCal version:", ihc.__version__)
#     print("Available models:", ihc.available_models())

#     model = ihc.create_model(
#         "swatplus_gwflow",
#         model_dir=".",
#     )

#     print("Model name:", model.model_name)
#     print("Model directory:", model.model_dir)
#     print("Model directory exists:", model.validate())


def main():
    model_dir = r"C:\Users\seonggpa\Documents\projects\watersheds\Pecos\Analysis\america-pecos\Scenarios\Default\TxtInOut_v02"
    model = ihc.create_model(
        "swatplus_gwflow",
        model_dir=model_dir
    )
    

    print(model.validate())

    df = model.io.read_channel_flow_day_wide()
    print(df.head())




if __name__ == "__main__":
    main()