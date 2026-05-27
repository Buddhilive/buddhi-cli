import { calculateTotal } from './utils';

export class OrderService {
    processOrder(items: string[]): number {
        return calculateTotal(items);
    }
}
