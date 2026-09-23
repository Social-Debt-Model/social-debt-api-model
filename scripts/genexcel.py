import pandas as pd

df_csv = pd.read_csv("dataset_test_100.csv")
df_template = pd.read_excel("dataset_prueba_cliente.xlsx")

for col in df_template.columns:
  if col not in df_csv.columns:
    df_csv[col] = pd.NA

df_csv[df_template.columns].to_excel("dataset_test_100.xlsx", index=False)
