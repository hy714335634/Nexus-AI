"""PubMed Literature Writing Agent Tools Package"""

from .literature_batch_processor import (
    load_marked_literature,
    get_next_batch,
    mark_batch_completed,
    get_processing_status,
    get_latest_review
)

from .review_writer import (
    write_batch_review,
    write_final_review,
    get_review_history
)

__all__ = [
    'load_marked_literature',
    'get_next_batch',
    'mark_batch_completed',
    'get_processing_status',
    'get_latest_review',
    'write_batch_review',
    'write_final_review',
    'get_review_history'
]

