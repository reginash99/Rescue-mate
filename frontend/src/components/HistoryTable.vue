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
                        <th></th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="(item, idx) in history" :key="idx">
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
                       <td>
                        <button @click="openModal(item)">View</button>
                       </td>
                    </tr>
                </tbody>
            </table>
        </div>
        <!-- Modal -->
        <div v-if="showModal" class="modal-overlay">
            <div class="modal-content">
            <button class="modal-close" @click="closeModal">×</button>
                <div v-if="selectedItem">
                    <p><strong>Transcription:</strong> {{ selectedItem.text }}</p>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref } from 'vue'

defineProps({
  history: {
    type: Array,
    default: () => []
  }
})

const showModal = ref(false)
const selectedItem = ref(null)

function openModal(item) {
  selectedItem.value = item
  showModal.value = true
}

function closeModal() {
  showModal.value = false
  selectedItem.value = null
}
// TODO: Remove??
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
    position: relative;
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
    background-color: var(--ternary-background);
    padding: 5px;
    color: var(--color-text-2);
}

.table_component td {
    padding: 5px;
    font-size: large;
}

.table_component tr:nth-child(even) td {
    background-color: var(--secondary-background);
}

.table_component tr:nth-child(odd) td {
    background-color: var(grid-item-backgound-color);
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

/* Modal View */

.modal-overlay {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(190, 188, 188, 0.288);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 100;
}

.modal-content {
    overflow-y: auto;
    overflow-x: auto;
    background: var(--color-background);
    border-radius: 12px;
    padding: 32px 24px 24px 24px;
    width: 70%;
    min-width: 250px;
    max-width: 500px;
    height: 70%;
    max-height: 400px;
    min-height: 250px;
    box-shadow: 0 8px 32px var(--shadow-color);
    position: relative;
    font-size: larger;
}

.modal-close {
    position: absolute;
    top: 12px;
    right: 16px;
    background: none;
    border: none;
    font-size: 2rem;
    cursor: pointer;
}
</style>