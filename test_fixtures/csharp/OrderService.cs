using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;

namespace Demo.Orders
{
    public interface IOrderRepository
    {
        Task<Order?> FindAsync(int id);
        void Save(Order order);
    }

    public record Order(int Id, decimal Amount, string? Customer, OrderStatus Status);

    public enum OrderStatus { New, Paid, Shipped, Cancelled }

    /// <summary>Service with a mix of C# constructs.</summary>
    [Serializable]
    public sealed class OrderService : IDisposable
    {
        private readonly IOrderRepository _repo;
        private readonly Dictionary<int, Order> _cache = new();
        private int _count;

        public OrderService(IOrderRepository repo) => _repo = repo ?? throw new ArgumentNullException(nameof(repo));

        public OrderService(IOrderRepository repo, string? name) : this(repo)
        {
            if (name != null)
            {
                Name = name;
            }
        }

        public string Name { get; set; } = "default";

        public int Count
        {
            get { return _count > 0 ? _count : 0; }
            set
            {
                if (value < 0 || value > 1000)
                {
                    throw new ArgumentOutOfRangeException(nameof(value));
                }
                _count = value;
            }
        }

        public bool IsBusy => _count > 10 && Name != "idle";

        // Package-private style: no access modifier
        void ResetCache()
        {
            foreach (var key in _cache.Keys.ToList())
            {
                if (_cache[key].Status == OrderStatus.Cancelled)
                {
                    _cache.Remove(key);
                }
            }
        }

        [Obsolete("use FindAsync")]
        public Order? Find(int id)
        {
            return _cache.TryGetValue(id, out var o) ? o : null;
        }

        public async Task<Order?> FindAsync(int id)
        {
            if (_cache.TryGetValue(id, out var cached))
            {
                return cached;
            }
            var order = await _repo.FindAsync(id);
            if (order is not null && order.Status != OrderStatus.Cancelled)
            {
                _cache[id] = order;
            }
            return order;
        }

        public decimal Discount(Order order) => order.Status switch
        {
            OrderStatus.New => 0m,
            OrderStatus.Paid when order.Amount > 1000 => 0.1m,
            OrderStatus.Paid => 0.05m,
            _ => 0m,
        };

        public string Describe(Order order)
        {
            switch (order.Status)
            {
                case OrderStatus.New:
                    return "new";
                case OrderStatus.Paid when order.Amount > 500:
                    return "big paid";
                case OrderStatus.Paid:
                    return "paid";
                default:
                    return "other";
            }
        }

        public string Label(Order order)
        {
            var path = @"C:\orders\";
            var quoted = @"He said ""if (x) { while (y) }"" twice";
            var json = """
                { "if": "(a && b)", "while": "{ }" }
                """;
            var text = $"Order {order.Id}: {(order.Amount > 100 ? "large" : "small")}";
            return path + quoted + json + text;
        }

        public IEnumerable<Order> Filter(IEnumerable<Order> orders, decimal min,
                                         bool includeCancelled,
                                         string? customer = null)
        {
            return orders.Where(o => o.Amount >= min
                                     && (includeCancelled || o.Status != OrderStatus.Cancelled)
                                     && (customer == null || o.Customer == customer));
        }

        public int Process(IList<Order> orders)
        {
            int processed = 0;
            for (int i = 0; i < orders.Count; i++)
            {
                var o = orders[i];
                try
                {
                    if (o.Amount <= 0)
                    {
                        continue;
                    }
                    else if (o.Status == OrderStatus.Shipped)
                    {
                        processed += 2;
                    }
                    else
                    {
                        processed++;
                    }
                }
                catch (InvalidOperationException ex) when (ex.Message.Contains("retry"))
                {
                    processed--;
                }
                catch (Exception)
                {
                    throw;
                }
            }
            return processed;
        }

        public int Retry(Func<int> action, int attempts)
        {
            int Attempt(int n)
            {
                try { return action(); }
                catch (TimeoutException) when (n < attempts) { return Attempt(n + 1); }
            }
            return Attempt(0);
        }

        public T FirstOrDefault<T>(IEnumerable<T> items, Func<T, bool> predicate) where T : class
        {
            foreach (var item in items)
            {
                if (predicate(item)) return item;
            }
            return default!;
        }

        public void Wait(Func<bool> ready)
        {
            int spins = 0;
            do
            {
                spins++;
            } while (!ready() && spins < 100);

            while (spins > 0)
            {
                spins--;
            }
        }

        public bool Validate(Order? order)
        {
            if (order is { Amount: > 0, Customer: not null } && order.Customer.Length > 2)
            {
                return true;
            }
            return order?.Customer?.Length > 0;
        }

        public string Name2(string? a) { a ??= "x"; return a.Length is > 0 and < 10 ? a : "long"; }

        public static Order operator +(OrderService s, Order o) => o with { Amount = o.Amount + s._count };

        public static explicit operator int(OrderService s)
        {
            return s._count;
        }

        public event EventHandler? Changed
        {
            add { if (value != null) _changed += value; }
            remove { _changed -= value; }
        }
        private EventHandler? _changed;

        public Order this[int id]
        {
            get
            {
                return _cache.TryGetValue(id, out var o) ? o : throw new KeyNotFoundException();
            }
        }

        public void Dispose()
        {
            lock (_cache)
            {
                using (var scope = new Scope())
                {
                    _cache.Clear();
                }
            }
        }

        ~OrderService()
        {
            Dispose();
        }

        private sealed class Scope : IDisposable
        {
            public void Dispose() { }
        }
    }

    public abstract class Handler<TIn, TOut>
    {
        public abstract TOut Handle(TIn input);

        protected virtual bool CanHandle(TIn input)
        {
            return input != null;
        }

        internal static IEnumerable<TOut> HandleAll(IEnumerable<TIn> inputs, Handler<TIn, TOut> h)
        {
            foreach (var i in inputs)
            {
                if (!h.CanHandle(i))
                    continue;
                yield return h.Handle(i);
            }
        }
    }
}
