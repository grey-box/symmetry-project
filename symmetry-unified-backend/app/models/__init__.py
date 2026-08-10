from app.models.api import (
    ListResponse,
    ModelSelectionResponse,
)
from app.models.comparison.models import (
    ArticleComparisonResponse,
    BaseCompareRequest,
    CompareRequest,
    CompareResponse,
    ComparisonResult,
    ExtraInfo,
    MissingInfo,
    ParagraphDiff,
    SectionCompareRequest,
    SectionCompareResponse,
    SemanticCompareRequest,
    SentenceDiff,
)
from app.models.comparison.models import (
    SectionDiff as SectionComparisonDiff,
)
from app.models.extraction.models import (
    FactExtractionRequest,
    FactExtractionResponse,
)
from app.models.revision import (
    DiffResponse,
    Flag,
    LagReport,
    Revision,
    RevisionDiffResponse,
    SectionChange,
)
from app.models.revision import (
    SectionDiff as RevisionSectionDiff,
)
from app.models.translation.models import ChunkedTranslateRequest
from app.models.wiki.analysis import (
    AnalysisResultsResponse,
    CitationAnalysisResponse,
    FinalAnalysisResponse,
    HeaderCount,
    InfoBoxAttribute,
    InfoBoxResponse,
    MultiLanguageScoreResponse,
    TableInfo,
    TableResponse,
)
from app.models.wiki.responses import (
    CitedArticle,
    SourceArticleResponse,
    StructuredArticleResponse,
    StructuredCitationResponse,
    StructuredReferenceResponse,
    StructuredSectionResponse,
    TranslateArticleResponse,
)
from app.models.wiki.structure import Article, Citation, Reference, Section

SectionDiff = SectionComparisonDiff

__all__ = [
    "AnalysisResultsResponse",
    "Article",
    "ArticleComparisonResponse",
    "BaseCompareRequest",
    "ChunkedTranslateRequest",
    "Citation",
    "CitationAnalysisResponse",
    "CitedArticle",
    "CompareRequest",
    "CompareResponse",
    "ComparisonResult",
    "DiffResponse",
    "ExtraInfo",
    "FactExtractionRequest",
    "FactExtractionResponse",
    "FinalAnalysisResponse",
    "Flag",
    "HeaderCount",
    "InfoBoxAttribute",
    "InfoBoxResponse",
    "LagReport",
    "ListResponse",
    "MissingInfo",
    "ModelSelectionResponse",
    "MultiLanguageScoreResponse",
    "ParagraphDiff",
    "Reference",
    "Revision",
    "RevisionDiffResponse",
    "RevisionSectionDiff",
    "Section",
    "SectionChange",
    "SectionCompareRequest",
    "SectionCompareResponse",
    "SectionComparisonDiff",
    "SectionDiff",
    "SemanticCompareRequest",
    "SentenceDiff",
    "SourceArticleResponse",
    "StructuredArticleResponse",
    "StructuredCitationResponse",
    "StructuredReferenceResponse",
    "StructuredSectionResponse",
    "TableInfo",
    "TableResponse",
    "TranslateArticleResponse",
]
