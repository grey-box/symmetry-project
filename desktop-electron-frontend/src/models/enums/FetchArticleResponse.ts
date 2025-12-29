export type FetchArticleResponse = {
  articleLanguages: Record<string, string>;
  sourceArticle: { text: string, title: string }
}