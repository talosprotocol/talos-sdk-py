import xml.etree.ElementTree as ET


class JUnitReport:
    def __init__(self):
        self.testsuites = []

    def add_testsuite(self, name, tests=0, failures=0, errors=0, time=0.0):
        suite = ET.Element(
            "testsuite",
            {
                "name": name,
                "tests": str(tests),
                "failures": str(failures),
                "errors": str(errors),
                "time": f"{time:.4f}",
            },
        )
        self.testsuites.append(suite)
        return suite

    def add_testcase(self, suite, name, classname, time=0.0):
        case = ET.SubElement(
            suite, "testcase", {"name": name, "classname": classname, "time": f"{time:.4f}"}
        )
        return case

    def add_failure(self, case, message, type="AssertionError"):
        failure = ET.SubElement(case, "failure", {"message": message, "type": type})
        failure.text = message

    def add_error(self, case, message, type="Error"):
        error = ET.SubElement(case, "error", {"message": message, "type": type})
        error.text = message

    def write(self, path):
        root = ET.Element("testsuites")
        for suite in self.testsuites:
            root.append(suite)

        tree = ET.ElementTree(root)
        ET.indent(tree, space="  ", level=0)
        tree.write(path, encoding="utf-8", xml_declaration=True)
