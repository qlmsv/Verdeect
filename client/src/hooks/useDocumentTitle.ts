import { useEffect } from 'react';

const DEFAULT_TITLE = 'ВердИИкт';

function useDocumentTitle(title: string) {
  useEffect(() => {
    document.title = title || DEFAULT_TITLE;
  }, [title]);
}

export default useDocumentTitle;
