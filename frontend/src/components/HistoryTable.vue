<template>
    <div class="main-table">
        <h1>History</h1>
        <div class="table_component" role="region" tabindex="0">
            <table responsive="True">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Time</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>
                            01
                        </td>
                        <td>
                            10.10.2025  12:00:00
                        </td>
                        <td>
                            <div class="sent">
                                Success
                                <i class="fa fa-check-circle"></i>
                            </div>
                        </td>
                    </tr>
                    <tr>
                        <td>
                            01
                        </td>
                        <td>
                            10.10.2025  12:00:00
                        </td>
                        <td>
                            <div class="sent">
                                Success
                                <i class="fa fa-check-circle"></i>
                            </div>
                        </td>
                    </tr>
                    <tr>
                        <td>
                            01
                        </td>
                        <td>
                            10.10.2025  12:00:00
                        </td>
                        <td>
                            <div class="sent">
                                Success
                                <i class="fa fa-check-circle"></i>
                            </div>
                        </td>
                    </tr>
                    <tr>
                        <td>
                            01
                        </td>
                        <td>
                            10.10.2025  12:00:00
                        </td>
                        <td>
                            <div class="sent">
                                Success
                                <i class="fa fa-check-circle"></i>
                            </div>
                        </td>
                    </tr>
                    <tr>
                        <td>
                            01
                        </td>
                        <td>
                            10-10-2025  12:00:00
                        </td>
                        <td>
                            <div class="sent">
                                Success
                                <i class="fa fa-check-circle"></i>
                            </div>
                        </td>
                    </tr>
                    <tr>
                        <td>
                            01
                        </td>
                        <td>
                            10/10/2025  12:00:00
                        </td>
                        <td>
                            <div class="sent">
                                Success
                                <i class="fa fa-check-circle"></i>
                            </div>
                        </td>
                    </tr>
                    <tr>
                        <td>
                            01
                        </td>
                        <td>
                            10.10.2025  12:00:00
                        </td>
                        <td>
                            <div class="sent">
                                Success
                                <i class="fa fa-check-circle"></i>
                            </div>
                        </td>
                    </tr>
                    <!-- <tr v-for="(item, idx) in history" :key="idx">
                        <td>
                            {{ idx + 1 }}
                        </td>
                        <td>
                            {{ item.timestamp ? formatTimestamp(item.timestamp) : item.timestamp }}
                        </td>
                        <td>
                            <div :class="item.text && item.text.trim() !== '' ? 'sent' : 'fail'">
                                {{ item.text && item.text.trim() !== '' ? 'Success' : 'Failed' }}
                                <i :class="item.text && item.text.trim() !== '' ? 'fa fa-check-circle' : 'fa fa-times-circle'"></i>
                            </div>
                        </td>
                    </tr> -->
                </tbody>
            </table>
        </div>
    </div>
</template>

<script setup>
defineProps({
  history: {
    type: Array,
    default: () => []
  }
})

function formatTimestamp(ts) {
  if (!ts || ts.length < 15) return ts || '';
  // Example: "20250810_145850"
  const year = ts.slice(0, 4);
  const month = ts.slice(4, 6);
  const day = ts.slice(6, 8);
  const hour = ts.slice(9, 11);
  const minute = ts.slice(11, 13);
  const second = ts.slice(13, 15);
  return `${day}/${month}/${year}  ${hour}:${minute}:${second}`;
}
</script>

<style scoped>

h1 {
    text-align: center;
}

.main-table {
    display: flex;
    padding: 10px;
    flex-direction: column;
    height: 100%;
    box-sizing: border-box;
    min-height: 0;
    width: 100%;
}

.table_component {
    min-height: 0;
    overflow-y: auto; 
    border: 1px none #dededf;
    border-collapse: collapse;
    border-spacing: 1px;
    width: 100%;
    min-width: 0;
    text-align: left;
    max-height: 100%;
}

.table_component table {
    width: 100%;
    border-collapse: collapse;
}

.table_component caption {
    caption-side: top;
    text-align: left;
}

.table_component th {
    position: sticky;
    top: 0;
    z-index: 2;
    border: 1px none #dededf;
    background-color: #000000;
    color: #ffffff;
    padding: 5px;
}

.table_component td {
    border: 1px none #dededf;
    padding: 5px;
    font-size: large;
}

.table_component tr:nth-child(even) td {
    background-color: #f3f2f2;
    color: #000000;
}

.table_component tr:nth-child(odd) td {
    background-color: #ffffff;
    color: #000000;
}

@media (max-width: 900px) {
    .table_component th {
        position: relative;
    }
}

.table_component tr td:first-child {
    border-top-left-radius: 18px;
    border-bottom-left-radius: 18px;
    padding-left: 13px !important;
}

.table_component tr td:last-child {
  border-top-right-radius: 18px;
  border-bottom-right-radius: 18px;
}

.table_component th:first-child {
  border-top-left-radius: 18px;
  border-bottom-left-radius: 18px;
  padding-left: 13px !important;
}

.table_component th:last-child {
  border-top-right-radius: 18px;
  border-bottom-right-radius: 18px;
}

.sent {
    i{
        color: #34A853;
    }
    display: inline-block;
    align-items: center;
    background-color: #D9FFC4;
    color: #1D6700;
    padding: 1px 5px;
    border-radius: 6px;
}

.fail {
    i{
        color: #CB0000
    }
    display: inline-block;
    align-items: center;
    background-color: #FFC4C4;
    color: #670000;
    padding: 1px 5px;
    border-radius: 6px;
}
</style>