import os
import shutil
import hashlib
import tarfile
import datetime

from django.conf import settings
from django.test import TestCase

from chronam.core.models import Batch, OcrDump

settings.OCR_DUMP_STORAGE = "/tmp/test_ocr_dumps"
dumps_dir = settings.OCR_DUMP_STORAGE

class OcrDumpTests(TestCase):
    fixtures = ["titles.json", "uuml_thys_sample.json", "countries.json", "awardee.json"]

    def setUp(self):
        if os.path.isdir(dumps_dir):
            shutil.rmtree(dumps_dir)
        os.mkdir(dumps_dir)

    def tearDown(self):
        pass #shutil.rmtree(dumps_dir)

    def test_new_dump(self):
        batch = Batch.objects.get(name="batch_uuml_thys_ver01")
        self.assertEqual(batch.page_count, 56)

        t0 = datetime.datetime.now()
        dump = OcrDump.new_from_batch(batch)
        self.assertEqual(dump.batch.name, "batch_uuml_thys_ver01")
        self.assertEqual(dump.name, "batch_uuml_thys_ver01.tar.bz2")
        self.assertEqual(dump.path, os.path.join(dumps_dir, "batch_uuml_thys_ver01.tar.bz2"))
        # size can actually vary based on the compression of the different dates
        # that are in the tarfile
        self.assertTrue(dump.size > 3500000)
        self.assertTrue(dump.size < 4500000)

        # make sure the sha1 looks good
        sha1 = hashlib.sha1()
        fh = open(dump.path)
        while True:
            buff = fh.read(2**16)
            if not buff: break
            sha1.update(buff)
        self.assertEqual(dump.sha1, sha1.hexdigest())

        # make sure there are the right number of things in the dump
        t = tarfile.open(dump.path, "r:bz2")
        members = t.getmembers()
        self.assertEqual(len(members), 112) # ocr xml and txt for each page
        self.assertEqual(members[0].size, 26282)

        # mtime on files in the archive should be just after we
        # created the OcrDump object from the batch
        t1 = datetime.datetime.fromtimestamp(members[0].mtime)
        self.assertTrue(t1 - t0 < datetime.timedelta(seconds=2))

        # when we delete the Batch, the OcrDump should be deleted
        # and so should the dump file on the filesystem
        path = dump.path
        batch.delete()
        self.assertEqual(Batch.objects.all().count(), 0)
        self.assertEqual(OcrDump.objects.all().count(), 0)
        self.assertTrue(not os.path.isfile(path))
