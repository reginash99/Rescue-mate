<script setup lang="ts">
defineProps<{
  msg: string
}>()
</script>

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
                        <td>101</td>
                        <td>26.04.2025 16:56:03</td>
                        <td>
                            <div class="sent">
                                Sent
                                <i class="fa fa-check-circle"></i>
                            </div>
                        </td>
                    </tr>
                    <tr>
                        <td>102</td>
                        <td>26.04.2025 16:56:03</td>
                        <td>
                            <div class="fail">
                                Failed
                                <i class="fa fa-times-circle"></i>
                            </div>
                        </td>
                    </tr>
                    <tr>
                        <td>103</td>
                        <td>26.04.2025 16:56:03</td>
                        <td>
                            <div class="sent">
                                Sent
                                <i class="fa fa-check-circle"></i>
                            </div>
                        </td>
                    </tr>
                    <tr>
                        <td>104</td>
                        <td>26.04.2025 16:56:03</td>
                        <td>
                            <div class="sent">
                                Sent
                                <i class="fa fa-check-circle"></i>
                            </div>
                        </td>
                    </tr>
                    <tr>
                        <td>104</td>
                        <td>26.04.2025 16:56:03</td>
                        <td>
                            <div class="sent">
                                Sent
                                <i class="fa fa-check-circle"></i>
                            </div>
                        </td>
                    </tr>
                    <tr>
                        <td>104</td>
                        <td>26.04.2025 16:56:03</td>
                        <td>
                            <div class="sent">
                                Sent
                                <i class="fa fa-check-circle"></i>
                            </div>
                        </td>
                    </tr>
                    <tr>
                        <td>104</td>
                        <td>26.04.2025 16:56:03</td>
                        <td>
                            <div class="sent">
                                Sent
                                <i class="fa fa-check-circle"></i>
                            </div>
                        </td>
                    </tr>
                    <tr>
                        <td>104</td>
                        <td>26.04.2025 16:56:03</td>
                        <td>
                            <div class="sent">
                                Sent
                                <i class="fa fa-check-circle"></i>
                            </div>
                        </td>
                    </tr>
                    <tr>
                        <td>104</td>
                        <td>26.04.2025 16:56:03</td>
                        <td>
                            <div class="sent">
                                Sent
                                <i class="fa fa-check-circle"></i>
                            </div>
                        </td>
                    </tr>
                    <tr>
                        <td>104</td>
                        <td>26.04.2025 16:56:03</td>
                        <td>
                            <div class="sent">
                                Sent
                                <i class="fa fa-check-circle"></i>
                            </div>
                        </td>
                    </tr>
                    <tr>
                        <td>104</td>
                        <td>26.04.2025 16:56:03</td>
                        <td>
                            <div class="sent">
                                Sent
                                <i class="fa fa-check-circle"></i>
                            </div>
                        </td>
                    </tr>
                    <tr>
                        <td>104</td>
                        <td>26.04.2025 16:56:03</td>
                        <td>
                            <div class="sent">
                                Sent
                                <i class="fa fa-check-circle"></i>
                            </div>
                        </td>
                    </tr>
                    <tr>
                        <td>104</td>
                        <td>26.04.2025 16:56:03</td>
                        <td>
                            <div class="sent">
                                Sent
                                <i class="fa fa-check-circle"></i>
                            </div>
                        </td>
                    </tr>
                    <tr>
                        <td>104</td>
                        <td>26.04.2025 16:56:03</td>
                        <td>
                            <div class="sent">
                                Sent
                                <i class="fa fa-check-circle"></i>
                            </div>
                        </td>
                    </tr>
                    <tr>
                        <td>104</td>
                        <td>26.04.2025 16:56:03</td>
                        <td>
                            <div class="sent">
                                Sent
                                <i class="fa fa-check-circle"></i>
                            </div>
                        </td>
                    </tr>
                </tbody>
            </table>
            </div>
        </div>
</template>

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