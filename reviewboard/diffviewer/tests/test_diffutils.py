from __future__ import unicode_literals
from reviewboard.diffviewer.models import FileDiff
class GetDiffFilesTests(TestCase):
    @add_fixtures(['test_users', 'test_scmtools'])
    @add_fixtures(['test_users', 'test_scmtools'])
    @add_fixtures(['test_users', 'test_scmtools'])
    @add_fixtures(['test_users', 'test_scmtools'])
class GetOriginalFileTests(SpyAgency, TestCase):
    fixtures = ['test_scmtools']
        """Testing get_original_file with an empty parent diff with a patch
        tool that does not accept empty diffs
        parent_diff = (
            b'diff --git a/empty b/empty\n'
            b'new file mode 100644\n'
            b'index 0000000..e69de29\n'
        diff = (
            b'diff --git a/empty b/empty\n'
            b'index e69de29..0e4b0c7 100644\n'
            b'--- a/empty\n'
            b'+++ a/empty\n'
            b'@@ -0,0 +1 @@\n'
            b'+abc123\n'
        )

        repository = self.create_repository(tool_name='Git')
        diffset = self.create_diffset(repository=repository)
        filediff = FileDiff.objects.create(
            diffset=diffset,
            source_file='empty',
            source_revision=PRE_CREATION,
            dest_file='empty',
            dest_detail='0e4b0c7')
        filediff.parent_diff = parent_diff
        filediff.diff = diff
        filediff.save()

        request_factory = RequestFactory()
            self.assertEqual(diff, parent_diff)
                filename=filename,
                error_output=_PATCH_GARBAGE_INPUT,
                orig_file=orig_file,
                new_file='tmp123-new',
                diff=b'',
                rejects=None)
                request=request_factory.get('/'),
            .filter(pk=filediff.pk)
            .first()
                request=request_factory.get('/'),
        """Testing get_original_file with an empty parent diff with a patch
        tool that does accept empty diffs
        parent_diff = (
            b'diff --git a/empty b/empty\n'
            b'new file mode 100644\n'
            b'index 0000000..e69de29\n'
        )

        diff = (
            b'diff --git a/empty b/empty\n'
            b'index e69de29..0e4b0c7 100644\n'
            b'--- a/empty\n'
            b'+++ a/empty\n'
            b'@@ -0,0 +1 @@\n'
            b'+abc123\n'
        repository = self.create_repository(tool_name='Git')
        diffset = self.create_diffset(repository=repository)
        filediff = FileDiff.objects.create(
            diffset=diffset,
            source_file='empty',
            source_revision=PRE_CREATION,
            dest_file='empty',
            dest_detail='0e4b0c7')
        filediff.parent_diff = parent_diff
        filediff.diff = diff
        filediff.save()

        request_factory = RequestFactory()
            self.assertEqual(diff, parent_diff)
                request=request_factory.get('/'),
                request=request_factory.get('/'),