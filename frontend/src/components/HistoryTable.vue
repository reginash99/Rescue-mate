<script setup lang="ts">
defineProps<{
  msg: string
}>()
</script>

<template>
    <vue-scrolling-table>
        <div class="main-table">
            <div class="table_component" role="region" tabindex="0">
            <h1>History</h1>
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
    display: block;
    padding: 10px;
    height: 100%;
}

table{
    max-width: 100%;
    width: 100%;
    height: 100%;
    max-height: 100%;
    table-layout: auto;
    overflow-x: scroll;
    overflow-y: scroll;
}

.table_component{
    max-height: inherit;
    overflow-y: scroll;
}

.table_component table {
    border: 1px none #dededf;
    height: 100%;
    width: 50vw;
    border-collapse: collapse;
    border-spacing: 1px;
    text-align: left;
    overflow-x: scroll;
    overflow-y: scroll;
}

.table_component caption {
    caption-side: top;
    text-align: left;
}

.table_component th {
    border: 1px none #dededf;
    background-color: #000000;
    color: #ffffff;
    padding: 5px;
    word-break: break-word;
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