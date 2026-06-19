<!--
 * @Author: 祝占朋 wb.zhuzp01@rd.netease.com
 * @Date: 2023-11-07 19:32:26
 * @LastEditors: Ianarua 306781523@qq.com
 * @LastEditTime: 2024-08-05 17:48:27
 * @FilePath: front_end/src/components/FileUploadDialog.vue
 * @Description:
-->
<template>
  <Teleport to="body">
    <a-modal
      v-model:open="modalVisible"
      :title="modalTitle"
      centered
      width="480px"
      wrap-class-name="upload-file-modal"
      destroy-on-close
    >
      <div class="file">
        <div class="box">
          <div class="before-upload-box">
            <input
              class="hide input"
              type="file"
              :accept="acceptList.join(',')"
              multiple
              @change="fileChange"
              @click="e => ((e.target as HTMLInputElement).value = '')"
            />
            <div class="before-upload">
              <div class="upload-text-box">
                <SvgIcon name="upload" />
                <p>
                  <span class="upload-text">
                    {{ common.dragUrl }}
                    <span class="blue">{{ common.click }}</span>
                  </span>
                </p>
              </div>
              <p class="desc">
                {{ common.updesc1 }}
              </p>
            </div>
          </div>
          <div
            v-show="uploadFileList.length > 0"
            class="upload-progress-box"
          >
            <div class="progress-header">
              <span class="title">{{ common.progress }}</span>
              <span class="file-count">{{ uploadFileList.length }} 个文件</span>
            </div>
            <ul class="progress-list">
              <li v-for="(item, index) in uploadFileList" :key="index" class="progress-item">
                <div class="file-info">
                  <span class="file-name">{{ item.file_name }}</span>
                  <span class="file-size">{{ formatFileSize(item.bytes) }}</span>
                </div>
                <div class="progress-bar-wrapper">
                  <div class="progress-bar-bg">
                    <div
                      class="progress-bar-fill"
                      :style="{ width: `${item.progress || 0}%`, backgroundColor: getProgressColor(item.status) }"
                    ></div>
                  </div>
                  <span class="progress-text">{{ item.progress || 0 }}%</span>
                </div>
                <div class="status-info">
                  <span v-if="item.stage" class="stage">{{ getStageName(item.stage) }}</span>
                  <span v-if="item.stage_status" class="stage-status">{{ getStageStatusText(item.stage_status) }}</span>
                  <span v-if="item.status === 'loading'" class="loading-text">{{ common.parsing }}</span>
                  <span v-else-if="item.status === 'success'" class="success-text">{{ common.upSucceeded }}</span>
                  <span v-else-if="item.status === 'error'" class="error-text">
                    {{ item.error_message || item.errorText || common.upFailed }}
                  </span>
                </div>
                <div v-if="item.progress_detail && hasCleanupFailures(item.progress_detail)" class="rollback-cleanup-details">
                  <div class="details-header">{{ common.cleanupFailuresTitle }}</div>
                  <ul class="details-list">
                    <li v-for="(f, idx) in getCleanupFailures(item.progress_detail)" :key="idx" class="detail-item failure">
                      <span class="store-name">[{{ f.store }}]</span>
                      <span class="residual-info">{{ common.leftResidual }}: {{ f.residual }}</span>
                      <span class="reason-text">{{ common.reason }}: {{ f.reason }}</span>
                    </li>
                  </ul>
                </div>
                <div v-if="item.status === 'error' && item.retryable" class="retry-section">
                  <a-button
                    type="link"
                    size="small"
                    class="retry-btn"
                    :loading="item.isRetrying"
                    @click="retryUploadFile(item)"
                  >
                    {{ common.retry }}
                  </a-button>
                </div>
              </li>
            </ul>
          </div>
        </div>
      </div>
      <template #footer>
        <a-button
          v-if="props.dialogType === 0"
          key="submit"
          type="primary"
          class="upload-btn"
          :disabled="!canSubmit"
          @click="handleOk"
        >
          {{ common.confirm }}
        </a-button>
        <a-button
          v-if="props.dialogType === 1"
          key="submit"
          type="primary"
          class="upload-btn"
          @click="handleCancel"
        >
          {{ common.cancel }}
        </a-button>
      </template>
    </a-modal>
  </Teleport>
</template>
<script lang="ts" setup>
import { apiBase } from '@/services';
import { useKnowledgeModal } from '@/store/useKnowledgeModal';
import { useKnowledgeBase } from '@/store/useKnowledgeBase';
import { useOptiionList } from '@/store/useOptiionList';
import SvgIcon from './SvgIcon.vue';
import { pageStatus } from '@/utils/enum';
import { IFileListItem, FileStage, FileStageStatus } from '@/utils/types';
import { message, notification } from 'ant-design-vue';
import { userId, userPhone } from '@/services/urlConfig';
import { getLanguage } from '@/language/index';
import { useUploadFiles } from '@/store/useUploadFiles';
import { useChatSetting } from '@/store/useChatSetting';
import urlResquest from '@/services/urlConfig';
import { resultControl } from '@/utils/utils';

// const { language } = storeToRefs(useLanguage());
const common = getLanguage().common;
const { setKnowledgeName, setModalVisible } = useKnowledgeModal();
const { setDefault } = useKnowledgeBase();
const { getDetails } = useOptiionList();
const { modalVisible, modalTitle } = storeToRefs(useKnowledgeModal());
const { currentId, currentKbName } = storeToRefs(useKnowledgeBase());
const { uploadFileList, uploadFileListQuick } = storeToRefs(useUploadFiles()); // 上传的文件列表
const { initUploadFileList } = useUploadFiles();
const { chatSettingFormActive } = storeToRefs(useChatSetting());

const props = defineProps({
  // 0为知识库上传，1为快速开始上传
  dialogType: {
    type: Number,
    require: true,
    default: 0,
  },
});

const timer = ref();

// const uploadFileList = ref([]); // 本次上传文件列表

//控制确认按钮 是否能提交
const canSubmit = computed(() => {
  return (
    currentId.value.length > 0 &&
    uploadFileList.value.length > 0 &&
    uploadFileList.value.every(item => item.status != 'loading')
  );
});

watch(
  () => modalVisible.value,
  () => {
    setKnowledgeName(currentKbName.value);
    // showUploadList.value = !!uploadFileList.value.length;
    // 如果是快速开始的便捷上传，将quick的引用给uploadFileList，因为便捷上传和知识库上传用两个data
    if (props.dialogType === 1) {
      uploadFileList.value = uploadFileListQuick.value;
    }
    if (!modalVisible.value && props.dialogType === 0) {
      initUploadFileList();
    }
  }
);

//是否显示上传文件列表 默认不显示
// const showUploadList = ref(false);

//允许上传的文件格式
const acceptList = [
  '.md',
  '.txt',
  '.pdf',
  '.jpg',
  '.png',
  '.jpeg',
  '.doc',
  '.docx',
  '.xls',
  '.xlsx',
  '.ppt',
  '.pptx',
  '.jsonl',
  '.eml',
  '.csv',
  // '.mp3',
  // '.wav',
];

// 文件大小限制
const fileSizeLimit = {
  document: 30 * 1024 * 1024, // 单个文档小于30M
  image: 5 * 1024 * 1024, // 单张图片小于5M
};

// 文件总大小限制
const totalSizeLimit = 125 * 1024 * 1024; // 文件总大小不超过125MB

//上传前校验
const beforeFileUpload = async (file, index) => {
  return new Promise((resolve, reject) => {
    console.log(file);
    // 检查文件扩展名是否被接受
    if (file.name && acceptList.includes('.' + file.name.split('.').pop().toLowerCase())) {
      // 根据文件类型设置大小限制
      const limit = file.type.startsWith('image/') ? fileSizeLimit.image : fileSizeLimit.document;
      const fileType = file.type.startsWith('image/') ? '图片' : '文档';

      // 检查文件大小是否超过限制
      if (file.size > limit) {
        reject(`单个${fileType}太大，不能超过 ${limit / 1024 / 1024} MB`);
        return;
      }

      // 如果文件通过所有检查，将其添加到上传列表
      uploadFileList.value.push({
        file_name: file.name,
        file: file,
        status: 'loading',
        text: common.uploading,
        file_id: '',
        order: uploadFileList.value.length,
        bytes: 0,
      });
      resolve(index);
    } else {
      reject(`${file.name}的文件格式不符`);
    }
  });
};

//input上传
const fileChange = e => {
  const files: FileList = e.target.files;
  // 先检查文件总大小
  let totalFilesSize = 0;
  Array.from(files).forEach(file => {
    totalFilesSize += file.size;
    // 检查文件总大小是否超过限制
    if (totalFilesSize >= totalSizeLimit) {
      message.error('文件总大小超过125MB');
      return;
    }
  });
  Array.from(files).forEach(async (file: any, index) => {
    try {
      await beforeFileUpload(file, index);
    } catch (e) {
      message.error(e);
    }
  });
  setTimeout(() => {
    uploadFileList.value.length && uplolad();
  });
};

const uplolad = async () => {
  // if (props.dialogType === 1) {
  handleCancel();
  // }
  const list = [];
  uploadFileList.value.forEach((file: IFileListItem) => {
    if (file.status == 'loading') {
      list.push(file);
    }
  });
  const formData = new FormData();
  for (let i = 0; i < list.length; i++) {
    formData.append('files', list[i]?.file);
  }
  formData.append('kb_id', currentId.value);
  formData.append('user_id', userId);
  formData.append('user_info', userPhone);
  formData.append('chunk_size', chatSettingFormActive.value.chunkSize.toString());
  // 上传模式，soft：文件名重复的文件不再上传，strong：文件名重复的文件强制上传
  formData.append('mode', 'soft');
  openNotification(0);
  fetch(apiBase + '/local_doc_qa/upload_files', {
    method: 'POST',
    body: formData,
  })
    .then(response => {
      if (response.ok) {
        return response.json(); // 将响应解析为 JSON
      } else {
        throw new Error('上传失败');
      }
    })
    .then(data => {
      // 在此处对接口返回的数据进行处理
      if (data.code === 200) {
        if (data.data.length === 0) {
          // 上传相同文件
          message.warn(data.msg || '出错了');
          notification.close('upload');
          list.forEach(item => {
            uploadFileList.value[item.order].status = 'error';
            uploadFileList.value[item.order].errorText = data?.msg || common.upFailed;
          });
          return;
        }
        openNotification(1);

        list.forEach((item, index) => {
          const fileData = data.data[index];
          let status = fileData.status;
          if (status == 'green' || status == 'gray') {
            status = 'success';
          } else {
            status = 'error';
          }
          uploadFileList.value[item.order].status = status;
          uploadFileList.value[item.order].file_id = fileData.file_id;
          uploadFileList.value[item.order].bytes = fileData.bytes;
          uploadFileList.value[item.order].progress = fileData.progress || 5;
          uploadFileList.value[item.order].stage = fileData.stage || 'upload';
          uploadFileList.value[item.order].errorText = common.upSucceeded;
        });

        startProgressPolling();
      } else {
        message.error(data.msg || '出错了');
        notification.close('upload');
        list.forEach(item => {
          uploadFileList.value[item.order].status = 'error';
          uploadFileList.value[item.order].errorText = data?.msg || common.upFailed;
        });
      }
    })
    .catch(e => {
      message.error(e.msg || '出错了');
      notification.close('upload');
    })
    .finally(() => {
      getDetails();
    });
};

// 0 上传中，1 上传成功,
const openNotification = (type: 0 | 1) => {
  notification[type ? 'success' : 'info']({
    key: 'upload',
    message: type ? '上传完成' : '上传中',
    description: type ? '' : '最多需要30s',
    duration: type ? 2.5 : 0,
  });
};

const handleOk = async () => {
  setModalVisible(false);
  setDefault(pageStatus.optionlist);
  await getDetails();
};

const handleCancel = () => {
  setModalVisible(false);
};

const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

const getStageName = (stage: string): string => {
  const stageMap: Record<string, string> = {
    upload: common.stageUpload,
    parse: common.stageParse,
    chunk: common.stageChunk,
    milvus_insert: common.stageMilvusInsert,
    es_index: common.stageEsIndex,
    rollback: common.stageRollback,
    cleanup: common.stageCleanup,
    completed: common.stageCompleted,
    failed: common.stageFailed,
  };
  return stageMap[stage] || stage;
};

const getStageStatusText = (status: string): string => {
  const statusMap: Record<string, string> = {
    pending: common.statusPending,
    running: common.statusRunning,
    success: common.statusSuccess,
    failed: common.statusFailed,
    partial_success: common.statusPartialSuccess,
  };
  return statusMap[status] || status;
};

const hasCleanupFailures = (progressDetail: any): boolean => {
  if (!progressDetail) return false;
  const ri = progressDetail.rollback_info;
  const ci = progressDetail.cleanup_info;
  return (ri?.has_failure || ci?.has_failure) && (ri?.failures?.length > 0 || ci?.failures?.length > 0);
};

const getCleanupFailures = (progressDetail: any): Array<any> => {
  if (!progressDetail) return [];
  const out: Array<any> = [];
  const ri = progressDetail.rollback_info;
  if (ri?.failures?.length > 0) {
    ri.failures.forEach((f: any) => out.push({ ...f, phase: 'rollback' }));
  }
  const ci = progressDetail.cleanup_info;
  if (ci?.failures?.length > 0) {
    ci.failures.forEach((f: any) => out.push({ ...f, phase: 'cleanup' }));
  }
  return out;
};

const getProgressColor = (status: string): string => {
  const colorMap: Record<string, string> = {
    gray: '#faad14',
    yellow: '#1890ff',
    green: '#52c41a',
    red: '#ff4d4f',
    loading: '#1890ff',
    success: '#52c41a',
    error: '#ff4d4f',
  };
  return colorMap[status] || '#1890ff';
};

const progressPollingTimer = ref<number | null>(null);

const startProgressPolling = () => {
  if (progressPollingTimer.value) {
    clearInterval(progressPollingTimer.value);
  }

  const pollProgress = async () => {
    const processingFiles = uploadFileList.value.filter(
      item => 
        item.file_id && 
        item.status !== 'error' && 
        (item.status === 'loading' || 
         item.progress === undefined || 
         item.progress < 100)
    );

    if (processingFiles.length === 0) {
      if (progressPollingTimer.value) {
        clearInterval(progressPollingTimer.value);
        progressPollingTimer.value = null;
      }
      return;
    }

    for (const file of processingFiles) {
      if (!file.file_id) continue;

      try {
        const res: any = await resultControl(
          await urlResquest.getFileProgress({
            file_id: file.file_id,
            kb_id: currentId.value,
          })
        );

        if (res && res.data) {
          file.progress = res.data.progress;
          file.stage = res.data.stage;
          file.stage_status = res.data.stage_status;
          file.error_code = res.data.error_code;
          file.error_message = res.data.error_message;
          file.retryable = res.data.retryable;
          file.retry_count = res.data.retry_count;
          file.progress_detail = res.data.progress_detail || null;

          if (res.data.status === 'green') {
            file.status = 'success';
          } else if (res.data.status === 'red') {
            file.status = 'error';
          } else {
            file.status = 'loading';
          }
        }
      } catch (e) {
        console.error('Progress polling error:', e);
      }
    }

    const allCompleted = uploadFileList.value.every(
      item => item.status === 'success' || item.status === 'error'
    );

    if (allCompleted) {
      if (progressPollingTimer.value) {
        clearInterval(progressPollingTimer.value);
        progressPollingTimer.value = null;
      }
    }
  };

  pollProgress();
  progressPollingTimer.value = window.setInterval(pollProgress, 3000);
};

const retryUploadFile = async (item: IFileListItem) => {
  try {
    item.isRetrying = true;
    const res = await resultControl(
      await urlResquest.retryFile({
        file_id: item.file_id,
        kb_id: currentId.value,
      })
    );
    message.success(common.retrySuccess);
    item.status = 'loading';
    item.progress = 0;
    item.stage = 'upload';
    item.stage_status = 'pending';
    item.error_message = undefined;
    item.error_code = undefined;
    item.retryable = false;
    startProgressPolling();
  } catch (e: any) {
    message.error(e.msg || common.retryFailed);
  } finally {
    item.isRetrying = false;
  }
};

onBeforeUnmount(() => {
  if (timer.value) {
    clearTimeout(timer.value);
  }
  if (progressPollingTimer.value) {
    clearInterval(progressPollingTimer.value);
    progressPollingTimer.value = null;
  }
});
</script>
<style lang="scss" scoped>
.file {
  margin-top: 16px;
  display: flex;

  .box {
    flex: 1;
    min-height: 248px;
    max-height: 400px;
    overflow-y: auto;
    border-radius: 6px;
    background: #f9f9fc;
    box-sizing: border-box;
    border: 1px dashed #ededed;
  }
}

.line-url {
  margin-top: 16px;
  height: 100px;
  display: flex;
  overflow: auto;

  .mt9 {
    margin-top: 9px;
  }

  :deep(.ant-input) {
    height: 30px;
  }

  :deep(.ant-form-item) {
    margin-bottom: 12px;
  }
}

.label {
  display: block;
  width: 82px;
  min-width: 82px;
  text-align: right;
  margin-right: 16px;
  color: $title1;

  .red {
    color: red;
  }
}

.before-upload-box {
  position: relative;
  width: 100%;
  height: 100%;

  &.uploading {
    height: 62px;
    border-bottom: 1px solid #ededed;
  }

  .hide {
    opacity: 0;
  }

  .input {
    position: absolute;
    width: 100%;
    height: 100%;
    z-index: 100;
  }

  .before-upload {
    width: 100%;
    position: absolute;
    left: 50%;
    top: 50%;
    transform: translate(-50%, -50%);
  }

  .upload-text-box {
    display: flex;
    align-items: center;
    justify-content: center;

    svg {
      width: 16px;
      height: 16px;
      margin-right: 4px;
      cursor: pointer;
    }

    .upload-text {
      font-weight: 500;
      font-size: 14px;
      color: $title1;
    }

    .blue {
      color: #5a47e5;
      cursor: pointer;
    }
  }

  .desc {
    color: $title3;
    text-align: center;
    margin-top: 8px;
    padding: 0 20px;
  }
}

.upload-box {
  &.upload-list {
    height: 188px;
  }

  .list {
    height: 188px;

    overflow: auto;

    li {
      display: flex;
      align-items: center;
      justify-content: space-around;
      height: 22px;
      margin-bottom: 20px;
      padding: 0 20px 0 16px;

      &:first-child {
        margin-top: 20px;
      }

      svg {
        width: 16px;
        height: 16px;
        margin-right: 4px;
      }

      .name {
        flex: 1;
        width: 0;
        margin-right: 20px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .status-box {
        display: flex;
        width: auto;
        align-items: center;
        justify-content: start;
        margin-right: 5px;

        .loading {
          width: 16px;
          height: 16px;
          margin-right: 4px;
          animation: 2s linear infinite loading;
        }

        .status {
          width: 60px;
          font-size: 14px;
          line-height: 22px;
          height: 22px;
          color: $title1;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
      }

      .delete {
        line-height: 22px;
        color: $title2;
        cursor: pointer;
      }
    }
  }

  .note {
    font-family: PingFang SC;
    font-size: 12px;
    font-weight: normal;
    margin-top: 12px;
    color: #999999;
    width: 330px;
  }
}

:deep(.ant-input) {
  height: 40px;
}

.upload-btn {
  background: #5147e5 !important;
}

.upload-progress-box {
  padding: 16px;
  background: #fff;
  border-top: 1px solid #ededed;

  .progress-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;

    .title {
      font-size: 14px;
      font-weight: 500;
      color: #333;
    }

    .file-count {
      font-size: 12px;
      color: #999;
    }
  }

  .progress-list {
    list-style: none;
    padding: 0;
    margin: 0;
    max-height: 200px;
    overflow-y: auto;

    .progress-item {
      padding: 12px;
      background: #f9f9fc;
      border-radius: 6px;
      margin-bottom: 8px;

      &:last-child {
        margin-bottom: 0;
      }

      .file-info {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;

        .file-name {
          font-size: 13px;
          color: #333;
          font-weight: 500;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
          max-width: 280px;
        }

        .file-size {
          font-size: 12px;
          color: #999;
          flex-shrink: 0;
          margin-left: 8px;
        }
      }

      .progress-bar-wrapper {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 6px;

        .progress-bar-bg {
          flex: 1;
          height: 6px;
          background: #e8e8e8;
          border-radius: 3px;
          overflow: hidden;

          .progress-bar-fill {
            height: 100%;
            border-radius: 3px;
            transition: width 0.3s ease;
          }
        }

        .progress-text {
          font-size: 12px;
          font-weight: 500;
          color: #666;
          min-width: 32px;
          text-align: right;
        }
      }

      .status-info {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 12px;

        .stage {
          color: #5a47e5;
          font-weight: 500;
        }

        .stage-status {
          color: #999;
        }

        .loading-text {
          color: #1890ff;
        }

        .success-text {
          color: #52c41a;
        }

        .error-text {
          color: #ff4d4f;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
          max-width: 200px;
        }
      }

      .retry-section {
        margin-top: 6px;

        .retry-btn {
          padding: 0;
          height: auto;
          font-size: 12px;
          color: #52c41a;
        }
      }

      .rollback-cleanup-details {
        margin-top: 6px;
        padding: 6px 8px;
        background: #fff2e6;
        border-left: 3px solid #fa8c16;
        border-radius: 2px;

        .details-header {
          font-size: 12px;
          font-weight: 600;
          color: #d46b08;
          margin-bottom: 4px;
        }

        .details-list {
          list-style: none;
          margin: 0;
          padding: 0;

          .detail-item {
            font-size: 11px;
            line-height: 1.5;
            margin-bottom: 3px;
            color: #613400;

            &.failure {
              color: #cf1322;
            }

            .store-name {
              font-weight: 600;
              margin-right: 6px;
            }

            .residual-info,
            .reason-text {
              margin-right: 6px;
            }
          }
        }
      }
    }
  }
}
</style>
<style lang="scss">
@keyframes loading {
  0% {
    transform: rotate(0deg);
  }

  50% {
    transform: rotate(180deg);
  }

  100% {
    transform: rotate(360deg);
  }
}
</style>
