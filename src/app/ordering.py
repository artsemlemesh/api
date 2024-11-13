from django.db.models import Count, Q
from rest_framework.filters import OrderingFilter

# Documentation
# https://docs.google.com/document/d/1O-Qyo9ZOA8Ueqc42PnzBxZfg6nRk9wnXDT_MdEBhXI8/edit


class ProductOrderingFilter(OrderingFilter):
    allowed_ordering_choices = ['relevance', 'newest']
    allowed_custom_filters = [
        'category', 'size',
        'brand', 'gender']

    def filter_item_match(self, request, queryset):
        # Filter by Count of Products where (Category AND Size AND Brand) > 0
        ordering = [f for f in request.query_params.keys(
        ) if f in self.allowed_custom_filters]

        if len(ordering) > 0:
            param_dict = dict(request.query_params)

            query_dict = {}
            for attr, values in param_dict.items():
                if attr in self.allowed_custom_filters:
                    query_dict.update({
                        f'{attr}__in': values
                    })

            queryset = queryset.annotate(
                matched_items=Count(Q(**query_dict)))
        return queryset

    def order_by_relevance(self, request, queryset):
        # Order by Count of Products where (Category AND Size AND Brand) match
        ordering = [f for f in request.query_params.keys(
        ) if f in self.allowed_custom_filters]
        query_dict = {}
        if len(ordering) > 0:
            param_dict = dict(request.query_params)
            for attr, values in param_dict.items():
                if attr in self.allowed_custom_filters:
                    query_dict.update({
                        f'{attr}__in': values
                    })

            queryset = queryset.annotate(
                matched_items=Count(Q(**query_dict))).order_by(
                '-matched_items', '-platform_margin',)
        return queryset.filter(Q(**query_dict))

    def filter_queryset(self, request, queryset, view):
        ordering_selection = request.query_params.get(self.ordering_param)
        if ordering_selection == 'newest':
            queryset = self.filter_item_match(request, queryset)
            queryset = queryset.order_by('-created')

        elif ordering_selection == 'relevance':
            queryset = self.order_by_relevance(request, queryset)
        else:
            queryset = self.order_by_relevance(request, queryset)
        return queryset
