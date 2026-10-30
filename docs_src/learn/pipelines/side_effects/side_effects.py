from data_joinery import Pipeline, side_effect, transform


@transform
def make_report() -> str:
    return "3 records"


@side_effect
def print_report(report: str) -> None:
    print(report)


pipeline = Pipeline()
report = pipeline.add_step(make_report)
printer = pipeline.add_step(print_report)
report >> printer

quiet_result = pipeline.run(include_side_effects=False)
print("Quiet run:", quiet_result.get_output(report))

pipeline.run()
print_report("Direct call")
