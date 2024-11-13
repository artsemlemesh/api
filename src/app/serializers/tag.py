import six
from taggit.serializers import TagListSerializerField


class ByndeTagListSerializer(TagListSerializerField):
    pass
    # TODO: Let's figure this out later.
    # def to_internal_value(self, value):
    #     if isinstance(value, six.string_types):
    #         value = value.split(',')

    #     if not isinstance(value, list):
    #         self.fail('not_a_list', input_type=type(value).__name__)

    #     for s in value:
    #         if not isinstance(s, six.string_types):
    #             self.fail('not_a_str')

    #         self.child.run_validation(s)
    #     return value
