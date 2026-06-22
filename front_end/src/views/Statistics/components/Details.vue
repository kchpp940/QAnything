<template>
  <div class="details-container">
    <div class="choose-area">
      <div class="left item-flex">
        <a-range-picker
          v-model:value="searchDate"
          :open="flag"
          @focus="pickerFocus"
          @blur="pickerBlur"
          @change="dateChange"
        />
        <a-input
          v-model:value="searchConfig.question"
          placeholder="提问内容"
          style="width: 200px; margin-left: 5px"
        />

        <a-tooltip title="search">
          <a-button
            shape="circle"
            :icon="h(SearchOutlined)"
            style="margin-left: 10px"
            @click="searchHandle"
          />
        </a-tooltip>
      </div>

      <div class="right item-flex">
        <div class="export-part button" @click="exportSelected">导出选中</div>
        <div class="export-all button" @click="exportAll">导出全部</div>
      </div>
    </div>
    <div class="table">
      <a-table
        :data-source="dataSource"
        :columns="columns"
        :pagination="paginationConfig"
        :loading="loading"
        :locale="{ emptyText: home.emptyText }"
        :scroll="{ x: 1000, y: 470 }"
        :row-selection="{ selectedRowKeys: [...selectedKeys], onSelect, onSelectAll }"
        :hide-on-single-page="true"
        :show-size-changer="false"
        @change="onChange"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'kbIds'">
            <a-tooltip placement="topLeft" color="#fff">
              <template #title>
                <span style="color: #666; user-select: text">{{ record.kbIds }}</span>
              </template>
              <span>{{ record.kbIds }}</span>
            </a-tooltip>
          </template>
          <template v-else-if="column.key === 'question'">
            <a-tooltip placement="topLeft" color="#fff">
              <template #title>
                <span style="color: #666; user-select: text">{{ record.question }}</span>
              </template>
              <span>{{ record.question }}</span>
            </a-tooltip>
          </template>
          <template v-else-if="column.key === 'answer'">
            <a-tooltip placement="topLeft" color="#fff">
              <template #title>
                <span style="color: #666; user-select: text">{{ record.answer }}</span>
              </template>
              <span>{{ record.answer }}</span>
            </a-tooltip>
          </template>
          <template v-else-if="column.key === 'options'">
            <a-popconfirm
              overlay-class-name="del-pop"
              placement="topRight"
              :title="statistics.exportTitle"
              :ok-text="common.confirm"
              :cancel-text="common.cancel"
              @confirm="confirmExportItem(record)"
            >
              <a-button type="link" class="export-item">
                {{ statistics.export }}
              </a-button>
            </a-popconfirm>
          </template>
        </template>
      </a-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { h } from 'vue';
import { downLoad, getContentDispositionByHeader } from '@/utils/utils';
import { getLanguage } from '@/language';
import { SearchOutlined } from '@ant-design/icons-vue';
import message from 'ant-design-vue/es/message';
import { api, IQARecord } from '@/services/api';

const { home, common, statistics } = getLanguage();

interface IQADetails {
  key: string;
  kbIds: string;
  question: string;
  answer: string;
  date: string;
}

function qaRecordToTable(record: IQARecord): IQADetails {
  return {
    key: record.id,
    kbIds: record.kbIdsDisplay,
    question: record.question,
    answer: record.answer,
    date: record.date,
  };
}

const dataSource = ref<IQADetails[]>([]);

const columns = [
  {
    title: '知识库Id',
    dataIndex: 'kbIds',
    key: 'kbIds',
    width: '10%',
    ellipsis: true,
  },
  {
    title: '提问',
    dataIndex: 'question',
    key: 'question',
    maxWidth: '35%',
    ellipsis: true,
  },
  {
    title: '回答',
    dataIndex: 'answer',
    key: 'answer',
    width: '35%',
    ellipsis: true,
  },
  {
    title: '时间',
    dataIndex: 'date',
    key: 'date',
    width: '10%',
  },
  {
    title: home.operate,
    key: 'options',
    width: '8%',
    fixed: 'right',
  },
];

const paginationConfig = ref({
  current: 1,
  pageSize: 6,
  total: 0,
  showSizeChanger: false,
  showTotal: (total: number) => `共 ${total} 条`,
});

const loading = ref(false);

const selectedKeys = ref<Set<string>>(new Set());

const onSelect = (selectedRow: { key: string }) => {
  const key = selectedRow.key;
  if (selectedKeys.value.has(key)) {
    selectedKeys.value.delete(key);
  } else {
    selectedKeys.value.add(key);
  }
};

const onSelectAll = (...args: unknown[]) => {
  const changeRows = args[2] as Array<{ key: string }>;
  changeRows.forEach(item => {
    const key = item.key;
    if (selectedKeys.value.has(key)) {
      selectedKeys.value.delete(key);
    } else {
      selectedKeys.value.add(key);
    }
  });
};

const searchConfig = ref({
  startDate: '',
  endDate: '',
  question: '',
});

const searchDate = ref<unknown[]>([]);

const flag = ref(false);

const pickerFocus = () => {
  flag.value = true;
};

const pickerBlur = () => {
  flag.value = false;
};

const dateChange = (_date: unknown, dateString: string[]) => {
  searchConfig.value.startDate = dateString[0] || '';
  searchConfig.value.endDate = dateString[1] || '';
};

const searchHandle = () => {
  const { startDate: time_start, endDate: time_end, question: query } = searchConfig.value;
  getQADetail({ time_start, time_end, query });
};

const getQADetail = async (params?: Record<string, unknown>) => {
  loading.value = true;
  try {
    const result = await api.statistics.getQAList({
      page_id: paginationConfig.value.current,
      page_limit: paginationConfig.value.pageSize,
      ...(params || {}),
    });
    paginationConfig.value.total = result.total;
    dataSource.value = result.records.map(qaRecordToTable);
  } catch (e) {
    message.error((e as { msg?: string }).msg || common.error);
  } finally {
    loading.value = false;
  }
};

const onChange = (pagination: { current: number }) => {
  paginationConfig.value.current = pagination.current;
  const { startDate: time_start, endDate: time_end, question: query } = searchConfig.value;
  getQADetail({ time_start, time_end, query });
};

const confirmExportItem = async (record: IQADetails) => {
  const res = await exportPost(record.key);
  if (res) beforeDownload(res);
};

const exportSelected = async () => {
  const res = await exportPost([...selectedKeys.value]);
  if (res) beforeDownload(res);
};

const exportAll = async () => {
  const res = await exportPost();
  if (res) beforeDownload(res);
};

const exportPost = async (qa_ids?: string[] | string) => {
  try {
    const params: { qa_ids?: string[] } = {};
    if (qa_ids) {
      params.qa_ids = Array.isArray(qa_ids) ? qa_ids : [qa_ids];
    }
    const res = await api.statistics.exportQA(params);
    return res;
  } catch (e) {
    message.error((e as { msg?: string }).msg || common.error);
    return null;
  }
};

const beforeDownload = (res: { headers: Headers; data: BlobPart }) => {
  const fileName = getContentDispositionByHeader(res.headers) || 'example.xlsx';
  const resFile = new File([res.data], fileName, { type: 'application/excel' });
  const url = URL.createObjectURL(resFile);
  downLoad(url, fileName);
};

onMounted(() => {
  getQADetail();
});
</script>

<style scoped lang="scss">
.details-container {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.choose-area {
  height: 32px;
  margin-bottom: 20px;
  display: flex;
  justify-content: space-between;
}

.item-flex {
  display: flex;

  .icon {
    width: 68px;
    height: 32px;
    @include flex-center;
    background: #ffffff;
    border-radius: 6px;
    border: 1px solid #e5e5e5;
    margin-left: 16px;
    font-size: 14px;
    color: #222222;
    cursor: default;

    img {
      width: 20px;
      height: 20px;
    }
  }

  .button {
    width: 88px;
    height: 32px;
    line-height: 22px;
    border-radius: 6px;
    opacity: 1;
    background: #ffffff;
    @include flex-center;
    font-size: 14px;
    color: #666666;
    border: 1px solid #e5e5e5;
    cursor: pointer;

    &.export-all {
      color: #ffffff;
      background: #5a47e5;
      margin-left: 16px;
    }
  }
}

.table {
  flex: 1;

  .ant-table {
    max-height: 517px;
  }

  .ant-table-pagination {
    margin-top: 10px;
  }

  .export-item {
    padding-left: 0;
  }
}
</style>
