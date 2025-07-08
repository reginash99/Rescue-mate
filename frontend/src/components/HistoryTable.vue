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
                    <tr v-for="(item, idx) in history" :key="idx">
                        <td>{{ idx + 1 }}</td>
                        <td>{{ item.timestamp ? item.timestamp : '' }}</td>
                        <td>
                            <!-- Success/sent if string is not empty, fail if string is empty -->
                            <div :class="item.text && item.text.trim() !== '' ? 'sent' : 'fail'">
                                {{ item.text && item.text.trim() !== '' ? 'Success' : 'Failed' }}
                                <i :class="item.text && item.text.trim() !== '' ? 'fa fa-check-circle' : 'fa fa-times-circle'"></i>
                            </div>
                        </td>
                    </tr>
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
</script>

<style scoped>
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
    border-spacing: 0;
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