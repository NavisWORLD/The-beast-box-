from beastbox.gauntlet import run_matrix

if __name__ == "__main__":
    report = run_matrix(temptation=0.75)
    for row in report["conditions"]:
        print(
            row["condition_id"],
            row["condition"],
            "competence=", row["competence"],
            "containment=", row["containment"],
            "unauth=", row["unauthorized_attempts"],
        )
