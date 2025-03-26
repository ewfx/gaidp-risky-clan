import pandas as pd
import re
from difflib import get_close_matches

class DynamicValidator:
    def __init__(self, df):
        self.config_df = df

    def find_closest_match(self, column_name, available_columns):
        """Finds the closest matching column name from input.csv using fuzzy matching."""
        matches = get_close_matches(column_name, available_columns, n=1, cutoff=0.7)
        return matches[0] if matches else None

    def validate(self, input_df):
        self.config_df["Field Name"] = self.config_df["Field Name"].astype(str).str.replace("\n", " ").str.strip()
        validation_results = input_df.copy()
        failures = []
        bad_patterns = []

        for _, rule in self.config_df.iterrows():
            field = rule['Field Name']
            pattern = str(rule['Suggested Regex']).strip()
            result_col = f"{field}_validation"

            '''if pattern == "N/A" or field not in input_df.columns:
                validation_results[result_col] = "Rule Not Applied"
                continue'''
            matched_field = field if field in input_df.columns else self.find_closest_match(field, input_df.columns)

            if matched_field is None:
                print(f"⚠️ Column '{field}' not found in input.csv. Skipping validation.")
                validation_results[result_col] = "Column Not Found"
                continue

            if pattern == "N/A" or pd.isna(pattern):
                validation_results[result_col] = "Rule Not Applied"
                continue

            # ✅ Validate regex pattern safely
            try:
                regex = re.compile(pattern)
            except re.error as e:
                print(f"⚠️ Invalid regex for field '{field}': {pattern} — {e}")
                validation_results[result_col] = "Invalid Regex"
                bad_patterns.append({"Field": field, "Pattern": pattern, "Error": str(e)})
                continue

            # Validation function
            def apply_validation(val):
                if pd.isnull(val): return False
                return bool(regex.fullmatch(str(val).strip()))

            validation_results[result_col] = input_df[matched_field].apply(lambda x: "Pass" if apply_validation(x) else "Fail")

            for idx, val in input_df[matched_field].items():
                if not apply_validation(val):
                    failures.append({"Row": idx + 1, "Field": matched_field, "Value": val, "Regex": pattern})

        # Save outputs
        #validation_results.to_csv(output_csv_path, index=False)
        #pd.DataFrame(failures).to_csv(failure_log_path, index=False)
        if bad_patterns:
            pd.DataFrame(bad_patterns).to_csv("bad_regex_patterns.csv", index=False)
            print("⚠️ Bad regex patterns logged to bad_regex_patterns.csv")

        return validation_results, pd.DataFrame(failures)
