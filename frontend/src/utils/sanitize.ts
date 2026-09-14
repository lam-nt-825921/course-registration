import DOMPurify from 'dompurify';

export function sanitizeHtml(dirtyHtml: string): string {
  if (typeof window === 'undefined') {
    return dirtyHtml.replace(/<[^>]*>?/gm, '');
  }
  return DOMPurify.sanitize(dirtyHtml, {
    ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'a', 'p', 'br', 'ul', 'ol', 'li', 'span', 'code', 'pre'],
    ALLOWED_ATTR: ['href', 'target', 'rel', 'class'],
  });
}
