import json
import tempfile
import unittest
from pathlib import Path
from build_index import build

class RepositoryTests(unittest.TestCase):
    def package(self):
        return dict(schema=1,license='CC0-1.0',author='Contributor',description='',config=dict(schema=1,name='Precision',game='Test game',aim={},graph={},bindings=[],output='TitanTwo',input_routing=dict(movement='Wasd',aim='Mouse')))
    def folder(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);root=Path(temp.name);(root/'configs').mkdir();return root
    def test_empty_repository_has_valid_index(self):
        self.assertEqual(json.loads(build(self.folder())),dict(schema=1,entries=[]))
    def test_full_config_becomes_searchable_listing(self):
        root=self.folder();(root/'configs/precision-123.json').write_text(json.dumps(self.package()),encoding='utf-8');entries=json.loads(build(root))['entries'];self.assertEqual(entries[0]['id'],'precision-123');self.assertEqual(entries[0]['game'],'Test game')
    def test_paid_and_invalid_packages_are_rejected(self):
        root=self.folder();p=self.package();p['price']=5;(root/'configs/paid.json').write_text(json.dumps(p),encoding='utf-8');self.assertRaises(ValueError,build,root)
    def test_mapping_behavior_settings_are_preserved(self):
        root=self.folder();p=self.package();p['config']['mapping']=dict(automatic=dict(buttons=False),behavior=dict(wait_enabled=True,wait_percent=20))
        path=root/'configs/mapping.json';path.write_text(json.dumps(p),encoding='utf-8')
        self.assertEqual(json.loads(build(root))['entries'][0]['id'],'mapping')
        self.assertEqual(json.loads(path.read_text())['config']['mapping'],p['config']['mapping'])
    def test_filename_and_oversized_package_are_rejected(self):
        root=self.folder();path=root/'configs/wrong.name.json';path.write_text(json.dumps(self.package()),encoding='utf-8');self.assertRaises(ValueError,build,root);path.unlink();(root/'configs/large.json').write_text(' '*4194305,encoding='utf-8');self.assertRaises(ValueError,build,root)

if __name__=='__main__':unittest.main()
