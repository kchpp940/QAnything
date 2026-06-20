import { IChatItem } from '@/utils/types';
import { useClipboard } from '@vueuse/core';
import { message } from 'ant-design-vue';
import { getLanguage } from '@/language';

const common = getLanguage().common;

export function useChatActions(options?: { onReAnswer?: (question: string) => void }) {
  const { copy } = useClipboard();

  const showSourceIdxs = ref<number[]>([]);

  const like = (item: IChatItem, e: MouseEvent) => {
    item.like = !item.like;
    item.unlike = false;
    if (item.like && e?.target) {
      const parentNode = (e.target as HTMLElement).parentNode as HTMLElement;
      if (parentNode) {
        parentNode.style.animation = 'shake ease-in .5s';
        const timer = setTimeout(() => {
          clearTimeout(timer);
          parentNode.style.animation = '';
        }, 600);
      }
    }
  };

  const unlike = (item: IChatItem) => {
    item.unlike = !item.unlike;
    item.like = false;
  };

  const myCopy = (item: IChatItem) => {
    copy(item.answer)
      .then(() => {
        item.copied = !item.copied;
        message.success(common.copySuccess, 1);
        const timer = setTimeout(() => {
          clearTimeout(timer);
          item.copied = !item.copied;
        }, 1000);
      })
      .catch(() => {
        message.error(common.copyFailed, 1);
      });
  };

  const reAnswer = (item: IChatItem) => {
    options?.onReAnswer?.(item.question);
  };

  const showDetail = (item: IChatItem, index: number) => {
    item.source[index].showDetailDataSource = !item.source[index].showDetailDataSource;
  };

  const hideDetail = (item: IChatItem, index: number) => {
    item.source[index].showDetailDataSource = false;
  };

  const showSourceList = (index: number) => {
    showSourceIdxs.value.push(index);
  };

  const hideSourceList = (index: number) => {
    showSourceIdxs.value = showSourceIdxs.value.filter(item => item !== index);
  };

  return {
    showSourceIdxs,
    like,
    unlike,
    myCopy,
    reAnswer,
    showDetail,
    hideDetail,
    showSourceList,
    hideSourceList,
  };
}
