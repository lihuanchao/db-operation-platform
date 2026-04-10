<template>
  <router-view />
</template>

<script setup lang="ts">
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  background-color: #f8f9fa;
}

#app {
  min-height: 100vh;
}

#app .main-content .page-header {
  margin-bottom: 4px !important;
}

#app .main-content .page-header h2 {
  margin: 0;
  font-size: 16px !important;
  line-height: 1.3;
}

#app .main-content .page-header p {
  margin: 2px 0 0 !important;
  font-size: 10px !important;
  line-height: 1.5;
}

#app .main-content .table-shell {
  padding: 8px !important;
}

#app .main-content .filter-card,
#app .main-content .table-card,
#app .main-content .detail-card,
#app .main-content .meta-card,
#app .main-content .result-card {
  margin-bottom: 4px !important;
}

#app .main-content .el-card + .el-card {
  margin-top: 4px !important;
}

#app .main-content .el-card__body {
  padding: 8px !important;
}

#app .main-content .el-card__header {
  padding: 6px 8px !important;
}

#app .main-content .el-form-item {
  margin-bottom: 4px !important;
}

#app .main-content .el-input__wrapper,
#app .main-content .el-select__wrapper,
#app .main-content .el-date-editor.el-input__wrapper {
  min-height: 28px !important;
}

#app .main-content .el-button {
  height: 28px !important;
  padding: 0 10px !important;
  font-size: 12px !important;
}

#app .main-content .table-actions,
#app .main-content .header-actions,
#app .main-content .panel-head-actions,
#app .main-content .log-actions,
#app .main-content .action-row,
#app .main-content .row-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

#app .main-content .table-actions .el-button + .el-button,
#app .main-content .header-actions .el-button + .el-button,
#app .main-content .panel-head-actions .el-button + .el-button,
#app .main-content .log-actions .el-button + .el-button,
#app .main-content .action-row .el-button + .el-button,
#app .main-content .row-actions .el-button + .el-button {
  margin-left: 0 !important;
}

#app .main-content .filter-actions .el-form-item__content {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: nowrap;
}

#app .main-content .filter-actions .el-button + .el-button {
  margin-left: 0 !important;
}

#app .main-content .el-table th.el-table__cell,
#app .main-content .el-table td.el-table__cell {
  padding: 4px 0 !important;
}

#app .main-content .el-pagination {
  margin-top: 6px !important;
}

@media (max-width: 960px) {
  #app .main-content .page-header h2 {
    font-size: 15px !important;
  }

  #app .main-content .table-shell {
    padding: 6px !important;
  }

  #app .main-content .el-card__body {
    padding: 6px !important;
  }

  #app .main-content .table-actions,
  #app .main-content .header-actions,
  #app .main-content .panel-head-actions,
  #app .main-content .log-actions,
  #app .main-content .action-row,
  #app .main-content .row-actions {
    flex-wrap: wrap;
  }
}
</style>
