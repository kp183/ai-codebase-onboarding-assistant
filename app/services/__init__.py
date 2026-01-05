# Services package for business logic components

from .search_service import SearchService, SearchResult, get_search_service
from .query_processing import QueryProcessingService, get_query_processing_service
from .predefined_queries import PredefinedQueryService, get_predefined_query_service
from .service_manager import ServiceManager, service_manager, get_service_manager

__all__ = [
    'SearchService',
    'SearchResult', 
    'get_search_service',
    'QueryProcessingService',
    'get_query_processing_service',
    'PredefinedQueryService',
    'get_predefined_query_service',
    'ServiceManager',
    'service_manager',
    'get_service_manager'
]