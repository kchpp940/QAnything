import html2canvas from 'html2canvas';
import { message } from 'ant-design-vue';
import { useChat } from '@/store/useChat';
import { getLanguage } from '@/language';

const common = getLanguage().common;

export function useDownloadChat(options?: { showLoading: Ref<boolean>; onClear?: () => void }) {
  const { showModal } = storeToRefs(useChat());
  const confirmLoading = ref(false);
  const content = ref('');
  const type = ref('');

  const downloadChat = () => {
    if (options?.showLoading?.value) return;
    type.value = 'download';
    showModal.value = true;
    content.value = common.saveTip;
  };

  const deleteChat = () => {
    if (options?.showLoading?.value) return;
    type.value = 'delete';
    showModal.value = true;
    content.value = common.clearTip;
  };

  const confirm = async () => {
    confirmLoading.value = true;
    if (type.value === 'download') {
      try {
        const ele = document.getElementById('chat-ul');
        const canvas = await html2canvas(ele as HTMLDivElement, {
          useCORS: true,
        });
        const imgUrl = canvas.toDataURL('image/png');
        const tempLink = document.createElement('a');
        tempLink.style.display = 'none';
        tempLink.href = imgUrl;
        tempLink.setAttribute('download', 'chat-shot.png');
        if (typeof tempLink.download === 'undefined') tempLink.setAttribute('target', '_blank');

        document.body.appendChild(tempLink);
        tempLink.click();
        document.body.removeChild(tempLink);
        window.URL.revokeObjectURL(imgUrl);
        message.success('下载成功');
        Promise.resolve();
      } catch (e) {
        message.error(e.message || e.msg || '出错了');
      }
    } else if (type.value === 'delete') {
      options?.onClear?.();
    }
    type.value = '';
    content.value = '';
    confirmLoading.value = false;
    showModal.value = false;
  };

  return {
    confirmLoading,
    content,
    type,
    downloadChat,
    deleteChat,
    confirm,
  };
}
