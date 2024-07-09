import os
import os.path
import unittest
from pyiron_snippets.resources import ResourceNotFound, ResourceResolver, ExecutableResolver

class TestResolvers(unittest.TestCase):
    """
    Class to test resolvers
    """

    @classmethod
    def setUpClass(cls):
        cls.static_path = os.path.join(os.path.dirname(__file__), "static", "resources")
        cls.res1 = os.path.join(cls.static_path, "res1")
        cls.res2 = os.path.join(cls.static_path, "res2")

    def test_resource_resolver(self):
        res = ResourceResolver([self.res1], "module1")
        self.assertEqual(set(res.search()),
                         {os.path.join(self.res1, "module1", "bin"),
                          os.path.join(self.res1, "module1", "data")},
                         "Simple search does not return all resources!")
        self.assertEqual(res.first(), tuple(res.search())[0],
                         "first does not return first result!")
        self.assertEqual(list(res.search()), res.list(), "list not equal to search!")
        with self.assertRaises(ResourceNotFound, msg="first does not raise error on non existing resource!"):
            res.first("nonexisting")
        res = ResourceResolver([self.res1, self.res2], "module3")
        self.assertTrue(len(res.list("empty.txt")) == 2,
                        msg="should find all instances of files with the same name.")

    def test_order(self):
        """search must return results in the order given by the resource paths."""
        self.assertTrue("res1" in ResourceResolver([self.res1, self.res2], "module3").first(),
                        "resolver does not respect order of given resource paths!")
        self.assertTrue("res2" in ResourceResolver([self.res2, self.res1], "module3").first(),
                        "resolver does not respect order of given resource paths!")
        self.assertEqual(tuple(os.path.basename(r) for r in ResourceResolver([self.res1], "module1").search()),
                         tuple(sorted(("bin", "data"))),
                         "search does not return results from the same folder in alphabetical order!")

    def test_chain(self):
        """chained resolvers must behave like normal resolvers."""
        chain = ResourceResolver([self.res1], "module3").chain(ResourceResolver([self.res2], "module3"))
        resol = ResourceResolver([self.res1, self.res2], "module3")

        self.assertEqual(chain.first(), resol.first(),
                         "first returns different result for chained and normal resolver!")
        self.assertEqual(tuple(chain.search()), tuple(resol.search()),
                         "search returns different result for chained and normal resolver!")

        self.assertIs(resol, resol.chain(), "Empty chain does not return the same resolver!")

    def test_executable(self):
        res = ExecutableResolver([self.res1], code="code1", module="module1")
        self.assertNotIn("versionnonexec", res.available_versions,
                      "ExecutableResolver must not list scripts that are not executable.")
        self.assertNotIn("wrong_format", res.available_versions,
                      "ExecutableResolver must not list scripts that do not follow the correct format.")
        self.assertEqual("version1", res.default_version,
                         "default version should be chosen in alphabetical order if not explicitly set.")
        res = ExecutableResolver([self.res1], code="code2", module="module1")
        self.assertEqual(res.default_version, "version2_default",
                         "default version should be chosen as explicitly set.")
        self.assertEqual(dict(res.search()), res.dict(), "dict not equal to search!")

    def test_resource_resolver_subdirs(self):
        """Resolver constructor should take any additional args to search sub directories."""
        res = ResourceResolver([self.res1], "module1", "bin")
        expected_results = {
            os.path.join(self.res1, "module1", "bin", path)
                for path in ("run_code1_versionnonexec.sh", "run_code1_version1.sh", "run_code1_version2.sh")
        }
        self.assertEqual(set(res.search("*code1*")), expected_results,
                        "Search with subdirectories does not return all resources!")

    def test_resource_resolver_name_globs(self):
            res = ResourceResolver([self.res1], "module1", "bin")
            expected_results = {
                os.path.join(self.res1, "module1", "bin", "run_code1_version1.sh"),
                os.path.join(self.res1, "module1", "bin", "run_code1_version2.sh"),
            }
            results = set(res.search(["*code1*version1.sh", "*code1*sion2.sh"]))
            self.assertEqual(results, expected_results,
                             "Search with multiple glob patterns does not return all resources!")

if __name__ == "__main__":
    unittest.main()
