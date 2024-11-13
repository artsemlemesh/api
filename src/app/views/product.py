from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import filters, mixins, status, viewsets, views, generics
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from app.filtersets import ProductFilterSet
from app.ordering import ProductOrderingFilter
from app.paginations import StandardResultsSetPagination

from rest_framework.views import APIView

from app.models import (
    Bundle, Product,
    BundleReport, BundleRating,
    ProductCategory, ProductBrand,
    ProductSize, ProductImage
)
from app.models.product import BG_REMOVAL_STATUS
from app.permissions import IsBundleOwner, IsProductImageOwner
from app.serializers.listing import (
    ProductSerializer,
    BundleSerializer, ProductDetailSerializer, BundlePurchaseSerializer,
    BundleCheckoutSerializer, BundleRatingCreateSerializer,
    SellingListSerializer, SellingDetailSerializer, SellingCreateSerializer,
    SellingPublishSerializer,
    BundleReceiveSerializer, SellingItemBackgroundRemovalStatus,
    BundleTrackerSerializer, BundleReportCreateSerializer,
    BundleReportSerializer, BundleRatingSerializer,
    SellingItemCreateSerializer, SellingItemSerializer,
    SellingItemDetailSerializer, ProductCategorySerializer,
    ProductBrandSerializer, ProductSizeSerializer,
    ProductBrandCreateSerializer, ProductImageSerializer,
    SellingImageBackgroundRemovalStatus
)
from app.utils.address import validate_usps_address
from cacheops import cache, CacheMiss
from django.contrib.auth import authenticate, login

class AddFavoriteAPIView(APIView):
    def post(self, request, pk):
        try:
            product = Product.objects.get(pk=pk)
            username = request.data.get('username')
            password = request.data.get('password')
            if not username or not password:
                return Response({'error': 'Username and password are required'}, status=status.HTTP_400_BAD_REQUEST)

            # Authenticate the user
            user = authenticate(request, username=username, password=password)
            if user is None:
                return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

            # Add product to the user's favorites
            product.favourite.add(user)
            return Response(ProductSerializer(product).data, status=status.HTTP_201_CREATED)

        except Product.DoesNotExist:
            return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    def get(self, request, pk):
        try:
            print('GET METHOD')
            # Assuming pk is the ID of the product
            product = Product.objects.get(pk=pk)
            user = request.user
            
            is_favorite = user in product.favourite.all()
            return Response({'is_favorite': is_favorite}, status=status.HTTP_200_OK)
        
        except Product.DoesNotExist:
            return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class RemoveFavoriteAPIView(APIView):
    def delete(self, request, pk):
        try:
            product = Product.objects.get(pk=pk)
            # Check user credentials
            username = request.data.get('username')
            password = request.data.get('password')

            if not username or not password:
                return Response({'error': 'Username and password are required'}, status=status.HTTP_400_BAD_REQUEST)

            # Authenticate the user
            user = authenticate(request, username=username, password=password)
            if user is None:
                return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

            # Remove product from the user's favorites
            product.favourite.remove(user)
            return Response({'status': 'Removed from favorites'}, status=status.HTTP_200_OK)

        except Product.DoesNotExist:
            return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    # def get(self, request, pk):
    #     try:
    #         print('GET METHOD - CHECK FAVORITE STATUS')
    #         product = Product.objects.get(pk=pk)
    #         user = request.user
            
    #         is_favorite = user in product.favourite.all()
    #         return Response({'is_favorite': is_favorite}, status=status.HTTP_200_OK)
        
    #     except Product.DoesNotExist:
    #         return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)
    #     except Exception as e:
    #         return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
class ProductViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet
):
    queryset = Product.objects.get_all_published()
    # print('querySet...', queryset)
    serializer_class = ProductSerializer
    filter_backends = (
        DjangoFilterBackend, ProductOrderingFilter, filters.SearchFilter)
    # print('filterBackends', filter_backends)
    filterset_class = ProductFilterSet
    search_fields = ['title']
    pagination_class = StandardResultsSetPagination

    http_method_names = ('get', 'patch', 'post')

    def get_serializer_class(self):
        serializer_map = {
            'retrieve': ProductDetailSerializer,
            'purchase': ProductDetailSerializer,
            'checkout': ProductDetailSerializer,
            'receive': ProductDetailSerializer,
            'tracking_details': ProductDetailSerializer,
        }

        return serializer_map.get(
            self.action, self.serializer_class
        )

    def update_(self, request, *args, **kwargs):
        print('update', self, request)
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(
            instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        return Response(serializer.data)

    def perform_update(self, serializer):
        print('perform_update...')
        serializer.save()

    def partial_update_(self, request, *args, **kwargs):
        print('partial...', self)
        kwargs['partial'] = True
        return self.update_(request, *args, **kwargs)

    def get_queryset(self):
        if self.action == 'retrieve':
            return Bundle.objects.get_all_exclude_draft()
        elif self.action == 'list':
            return Product.objects.get_all_published()
        elif self.action == 'purchased_by':
            return self.request.user.purchased_listings.all()

        qs = Bundle.objects.get_all_published(self.request.user)
        if not self.request.user.is_anonymous and \
                self.request.user.is_superuser:
            qs = qs.filter(hidden=False)
        return qs

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(
        detail=True, methods=['patch'],
        url_path='purchase', url_name='purchase',
        permission_classes=[IsAuthenticated]
    )
    def purchase(self, request, *args, **kwargs):
        return self.partial_update_(request, *args, **kwargs)

    @action(
        detail=True, methods=['get'],
        url_path='tracking_details', url_name='tracking_details',
        permission_classes=[IsAuthenticated]
    )
    def tracking_details(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @action(
        detail=True, methods=['patch'],
        url_path='return', url_name='return',
        permission_classes=[IsAuthenticated]
    )
    def return_(self, request, *args, **kwargs):
        print('empty...')
        # NOTE: DO SOMETHING HERE.
        return Response(status=status.HTTP_200_OK)

    @action(
        detail=True, methods=['patch'],
        url_path='receive', url_name='receive',
        permission_classes=[IsAuthenticated]
    )
    def receive(self, request, *args, **kwargs):
        return self.partial_update_(request, *args, **kwargs)

    @action(
        detail=False, methods=['get'],
        url_name='purchased_by', url_path='purchased_by',
        permission_classes=[IsAuthenticated]
    )
    def purchased_by(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    # @action(detail=True, methods=['post', 'get'], url_path='add-favorite')
    # def add_favorite(self, request, pk=None):
    #     print('add_favorite...BACKEND')
    #     try:
    #         product = self.get_object()
    #         user = request.user
    #         product.favourite.add(user)
    #         return Response({'status': 'added to favorites'}, status=status.HTTP_201_CREATED)
    #     except Exception as e:
    #         return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    # @action(detail=True, methods=['post'], url_path='remove-favorite')
    # def remove_favorite(self, request, pk=None):
    #     product = self.get_object()
    #     user = request.user
    #     product.favourite.remove(user)
    #     return Response({'status': 'removed from favorites'}, status=status.HTTP_204_NO_CONTENT)

class SellingImageViewSet(viewsets.ModelViewSet):
    queryset = ProductImage.objects.all()
    serializer_class = ProductImageSerializer
    permission_classes = [IsProductImageOwner]

    def get_serializer_class(self):
        if self.action == 'progress':
            return SellingImageBackgroundRemovalStatus

        return self.serializer_class

    def retrieve(self, request, pk=None):
        image = get_object_or_404(ProductImage, pk=pk)
        if image.bg_removal_status in [BG_REMOVAL_STATUS.pending, BG_REMOVAL_STATUS.in_progress]:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return super().retrieve(request, pk=pk)

    @action(
        detail=False, methods=['put'],
        url_name='remove-background', url_path='remove-background', permission_classes=[IsAuthenticated]
    )
    def remove_background(self, request):
        data = request.data
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        instance.request_to_remove_background()
        return Response({"id": instance.id}, status=status.HTTP_202_ACCEPTED)

    @action(
        detail=False, methods=['post'],
        url_path=r'progress/(?P<pk>\d+)', url_name='progress'
    )
    def progress(self, request, pk=None, *args, **kwargs):
        image = get_object_or_404(ProductImage, pk=pk)
        SerializerClass = self.get_serializer_class()
        serializer = SerializerClass(image)
        if image.bg_removal_status != BG_REMOVAL_STATUS.done:
            return Response(serializer.data, status=status.HTTP_409_CONFLICT)
        return Response(serializer.data)


class SellingViewSet(viewsets.ModelViewSet):
    queryset = Bundle.objects.all()
    serializer_class = SellingDetailSerializer
    filterset_class = ProductFilterSet
    pagination_class = StandardResultsSetPagination
    permission_classes = [IsAuthenticated]
    ordering_fields = ('buyer_price', 'created')
    ordering = ('-created')

    def get_queryset(self):
        return self.queryset.filter(created_by=self.request.user)

    def get_serializer_class(self):
        if self.action == 'create':
            return SellingCreateSerializer
        elif self.action == 'list':
            return SellingListSerializer
        elif self.action == 'publish':
            return SellingPublishSerializer
        else:
            return SellingDetailSerializer

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        return Response({
            'status': 201,
            'message': 'Bundle Created',
            'data': response.data
        })

    def destroy(self, request, *args, **kwargs):
        super().destroy(request, *args, **kwargs)
        return Response({
            'status': 200,
            'message': 'Bundle Deleted'})

    @action(
        detail=True, methods=['patch'],
        url_name='publish', url_path='publish'
    )
    def publish(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

    @action(
        detail=True, methods=['patch'],
        url_name='unpublish', url_path='unpublish'
    )
    def unpublish(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)


class SellingSuppliesView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        data = request.data
        user = request.user
        address = {
            'city': user.city,
            'state': user.state,
            'postal_code': user.postal_code,
            'country': 'US',
        }
        address_lines = filter(
            None, [user.address_line_1, user.address_line_2])
        street_address = "\n".join(address_lines)

        if street_address and len(validate_usps_address(street_address=street_address, **address)[1]) == 0:
            if len(data):
                boxes = [i.get('item') for i in data if i.get('item') in [
                    'LARGE_FLAT_RATE_BOX',
                    'MEDIUM_FLAT_RATE_BOX',
                    'PADDED_FLAT_RATE_ENVELOPE']]
            user.send_bundle_kits(boxes)
        else:
            return Response({
                'status': 400,
                'message': 'Invalid Address'
            }, status=status.HTTP_400_BAD_REQUEST)
        return Response({
            'status': 200,
            'message': 'Supplies Created'
        })


class SellingItemViewSet(viewsets.ModelViewSet):
    serializer_class = SellingItemDetailSerializer
    permission_classes = [IsBundleOwner]
    queryset = Product.objects.all()

    def get_queryset(self):
        qs = self.queryset.filter(created_by=self.request.user)
        return qs.filter(listing=self.get_listing_object()) \
            if self.get_listing_object() else qs

    def get_serializer_class(self):
        if self.action == 'create':
            return SellingItemCreateSerializer
        elif self.action == 'list':
            return SellingItemSerializer
        elif self.action == 'progress':
            return SellingItemBackgroundRemovalStatus
        else:
            return self.serializer_class

    def get_listing_object(self) -> Bundle:
        listing_pk = self.request.parser_context['kwargs'].get('listing_pk')
        return Bundle.objects.get(pk=listing_pk) if listing_pk else None

    def create(self, request, *args, **kwargs):
        if self.get_listing_object().status not in ['draft', 'published']:
            raise Exception(
                'Status of associated listing should be draft or published')

        response = super().create(request, *args, **kwargs)
        return Response({
            'status': status.HTTP_201_CREATED,
            'message': 'Bundle Item Created',
            'data': response.data
        })

    @action(
        detail=True, methods=['get'],
        url_path='progress', url_name='progress'
    )
    def progress(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    @action(
        detail=True, methods=['delete'],
        url_path=r'remove-image/(?P<image_id>\d+)', url_name='Remove Image'
    )
    def remove_image(self, request, *args, **kwargs):
        pk = kwargs.get("image_id")
        get_object_or_404(ProductImage, pk=pk).delete()
        return self.retrieve(request, *args, **kwargs)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)


class BundleReportViewSet(viewsets.ModelViewSet):
    queryset = BundleReport.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = BundleReportSerializer
    filter_backends = [
        DjangoFilterBackend,
        filters.OrderingFilter,
        filters.SearchFilter
    ]
    filter_fields = ["reported", "listing", "reported_by"]
    ordering_fields = ["created", "reported"]

    def get_serializer_class(self):
        if self.action.lower() in ['list', 'retrieve']:
            return self.serializer_class
        return BundleReportCreateSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.is_superuser or user.is_staff:
            return queryset
        return queryset.filter(reported_by=user)


class BundleRatingViewSet(viewsets.ModelViewSet):
    queryset = BundleRating.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = BundleRatingSerializer
    filter_backends = [
        DjangoFilterBackend,
        filters.OrderingFilter,
        filters.SearchFilter
    ]
    filter_fields = ["listing", "rated_by"]

    def get_serializer_class(self):
        if self.action.lower() in ['list', 'retrieve']:
            return self.serializer_class
        return BundleRatingCreateSerializer


# class ProductCategoryViewSet(viewsets.ModelViewSet):
#     queryset = ProductCategory.objects.filter(parent__isnull=True)
#     # permission_classes = [IsAuthenticated]
#     serializer_class = ProductCategorySerializer
#     filter_backends = [
#         DjangoFilterBackend,
#         filters.OrderingFilter,
#         filters.SearchFilter
#     ]
#     filter_fields = ["parent"]
#     search_fields = ["name"]

#     def get_serializer_class(self):
#         if self.action.lower() in ['list', 'retrieve']:
#             return self.serializer_class
#         return ProductCategoryCreateSerializer


class ProductBrandSuggestAPIView(generics.CreateAPIView):
    # serializer_class = ProductBrandCreateSerializer
    serializer_class = ProductBrandCreateSerializer
    permission_classes = [IsAuthenticated]


class ProductOptionView(views.APIView):
    def get(self, request, format=None, **kwargs):
        try:
            resp = cache.get('item_options')
        except CacheMiss:
            listing_item_size = ProductSize.objects.filter(
                parent__isnull=True)
            listing_item_size_serializer = ProductSizeSerializer(
                listing_item_size, many=True)

            listing_item_category = ProductCategory.objects.filter(
                parent__isnull=True)
            listing_item_category_serializer = ProductCategorySerializer(
                listing_item_category, many=True)

            listing_item_brand = ProductBrand.objects.filter(
                parent__isnull=True)
            listing_item_brand_serializer = ProductBrandSerializer(
                listing_item_brand, many=True)
            resp = {
                'sizes': listing_item_size_serializer.data,
                'categories': listing_item_category_serializer.data,
                'brands': listing_item_brand_serializer.data,
            }
            cache.set('item_options', resp, timeout=None)
        return Response(resp)
