import { useChatSource } from '@/store/useChatSource';
import { message } from 'ant-design-vue';
import urlResquest, { resultControl } from '@/services/urlConfig';

const supportSourceTypes = [
  'md',
  'txt',
  'pdf',
  'jpg',
  'png',
  'jpeg',
  'doc',
  'docx',
  'xls',
  'xlsx',
  'ppt',
  'pptx',
  'jsonl',
  'csv',
  'eml',
];

const b64Types = [
  'text/markdown',
  'text/plain',
  'application/pdf',
  'image/jpeg',
  'image/png',
  'image/jpeg',
  'application/msword',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'application/vnd.ms-excel',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  'application/vnd.ms-powerpoint',
  'application/vnd.openxmlformats-officedocument.presentationml.presentation',
  'application/jsonl',
  'text/csv',
  'message/rfc822',
];

function getB64Type(suffix: string) {
  const index = supportSourceTypes.indexOf(suffix);
  return b64Types[index];
}

export function checkFileType(filename: string) {
  if (!filename) {
    return false;
  }
  const arr = filename.split('.');
  if (arr.length) {
    const suffix = arr.pop();
    if (supportSourceTypes.includes(suffix)) {
      return true;
    }
  }
  return false;
}

export function useChatSourceFile() {
  const { setChatSourceVisible, setSourceType, setSourceUrl, setTextContent } = useChatSource();

  const queryFile = async (file: any) => {
    try {
      setSourceUrl(null);
      const res: any = await resultControl(await urlResquest.getFile({ file_id: file.file_id }));
      const suffix = file.file_name.split('.').pop();
      const b64Type = getB64Type(suffix);
      const base64Content = res.file_base64 || res.base64_content;
      setSourceType(suffix);
      setSourceUrl(`data:${b64Type};base64,${base64Content}`);
      if (suffix === 'txt' || suffix === 'md' || suffix === 'csv' || suffix === 'eml') {
        const decodedTxt = atob(base64Content);
        const correctStr = decodeURIComponent(escape(decodedTxt));
        setTextContent(correctStr);
        setChatSourceVisible(true);
      } else {
        setChatSourceVisible(true);
      }
    } catch (e) {
      message.error(e.msg || '获取文件失败');
    }
  };

  const handleChatSource = (file: any) => {
    const isSupport = checkFileType(file.file_name);
    if (isSupport) {
      queryFile(file);
    }
  };

  return {
    checkFileType,
    handleChatSource,
    queryFile,
  };
}
