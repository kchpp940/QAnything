import { IDataSourceItem } from '@/utils/types';
import { useChatSourceFile } from './useChatSourceFile';

export interface NormalizedSourceItem extends IDataSourceItem {
  linkUrl: string | null;
  isExternalLink: boolean;
  isPreviewable: boolean;
}

export interface SourceGroup {
  type: 'kb' | 'web' | 'other';
  label: string;
  items: NormalizedSourceItem[];
}

export function useSourcePresenter() {
  const { checkFileType, handleChatSource } = useChatSourceFile();

  const showSourceIdxs = ref<number[]>([]);
  const showDetailIdxs = ref<Record<number, number[]>>({});

  const normalizeSource = (source: IDataSourceItem): NormalizedSourceItem => {
    const linkUrl = source.file_url || source.file_id;
    const isExternalLink = !!(linkUrl && typeof linkUrl === 'string' && linkUrl.startsWith('http'));
    const isPreviewable = checkFileType(source.file_name || '');

    return {
      ...source,
      linkUrl,
      isExternalLink,
      isPreviewable,
    };
  };

  const normalizeSources = (sources: IDataSourceItem[]): NormalizedSourceItem[] => {
    return sources.map(normalizeSource);
  };

  const groupSources = (sources: IDataSourceItem[]): SourceGroup[] => {
    const normalized = normalizeSources(sources);
    const kbItems: NormalizedSourceItem[] = [];
    const webItems: NormalizedSourceItem[] = [];
    const otherItems: NormalizedSourceItem[] = [];

    normalized.forEach(item => {
      if (item.isExternalLink) {
        webItems.push(item);
      } else if (item.file_id) {
        kbItems.push(item);
      } else {
        otherItems.push(item);
      }
    });

    const groups: SourceGroup[] = [];
    if (kbItems.length) {
      groups.push({ type: 'kb', label: '知识库来源', items: kbItems });
    }
    if (webItems.length) {
      groups.push({ type: 'web', label: '联网搜索', items: webItems });
    }
    if (otherItems.length) {
      groups.push({ type: 'other', label: '其他来源', items: otherItems });
    }

    return groups;
  };

  const showSourceList = (index: number) => {
    if (!showSourceIdxs.value.includes(index)) {
      showSourceIdxs.value.push(index);
    }
  };

  const hideSourceList = (index: number) => {
    showSourceIdxs.value = showSourceIdxs.value.filter(i => i !== index);
  };

  const isSourceVisible = (index: number): boolean => {
    return showSourceIdxs.value.includes(index);
  };

  const showDetail = (msgIndex: number, sourceIndex: number) => {
    if (!showDetailIdxs.value[msgIndex]) {
      showDetailIdxs.value[msgIndex] = [];
    }
    if (!showDetailIdxs.value[msgIndex].includes(sourceIndex)) {
      showDetailIdxs.value[msgIndex].push(sourceIndex);
    }
  };

  const hideDetail = (msgIndex: number, sourceIndex: number) => {
    if (showDetailIdxs.value[msgIndex]) {
      showDetailIdxs.value[msgIndex] = showDetailIdxs.value[msgIndex].filter(
        i => i !== sourceIndex
      );
    }
  };

  const isDetailVisible = (msgIndex: number, sourceIndex: number): boolean => {
    return !!(
      showDetailIdxs.value[msgIndex] && showDetailIdxs.value[msgIndex].includes(sourceIndex)
    );
  };

  const toggleDetail = (msgIndex: number, sourceIndex: number) => {
    if (isDetailVisible(msgIndex, sourceIndex)) {
      hideDetail(msgIndex, sourceIndex);
    } else {
      showDetail(msgIndex, sourceIndex);
    }
  };

  const handleSourceClick = (sourceItem: IDataSourceItem) => {
    handleChatSource(sourceItem);
  };

  return {
    showSourceIdxs,
    showDetailIdxs,
    normalizeSource,
    normalizeSources,
    groupSources,
    showSourceList,
    hideSourceList,
    isSourceVisible,
    showDetail,
    hideDetail,
    isDetailVisible,
    toggleDetail,
    handleSourceClick,
    checkFileType,
  };
}
